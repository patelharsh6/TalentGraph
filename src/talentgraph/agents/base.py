"""Agent protocol and registry. `run_agent()` (retries, timeouts, AgentRun records) (Step 4.6)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

import structlog

from talentgraph.core.schemas.messages import (
    AgentError,
    AgentMessage,
    AgentName,
    AgentResult,
    AgentRun,
    QualityScore,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from talentgraph.orchestrator.state import PipelineState

log = structlog.get_logger(__name__)


class Agent(Protocol):
    name: AgentName

    async def startup(self) -> None: ...

    async def shutdown(self) -> None: ...

    async def handle(self, msg: AgentMessage) -> AgentResult: ...


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[AgentName, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.name] = agent

    def get(self, name: AgentName) -> Agent:
        return self._agents[name]

    async def startup(self) -> None:
        for agent in self._agents.values():
            await agent.startup()

    async def shutdown(self) -> None:
        for agent in reversed(list(self._agents.values())):
            await agent.shutdown()


async def run_agent(
    agent_name: AgentName,
    action: Callable[[], Coroutine[Any, Any, AgentResult]],
    state: PipelineState,
    *,
    timeout_s: float = 30.0,
    max_attempts: int = 3,
    session: AsyncSession | None = None,
) -> AgentResult:
    """Execute an agent action inside the pipeline with timeouts, retries, and run tracking."""
    result: AgentResult | None = None

    for attempt in range(1, max_attempts + 1):
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()
        try:
            result = await asyncio.wait_for(action(), timeout=timeout_s)
            latency_ms = int((time.perf_counter() - t0) * 1000)

            # Record successful run
            run = AgentRun(
                trace_id=state.trace_id,
                agent=agent_name,
                attempt=attempt,
                status=result.status,
                latency_ms=latency_ms,
                quality=result.quality.score if result.quality else None,
                error_code=None if result.status != "failed" else "agent_failed",
                started_at=started_at,
            )
            state.record_run(run)

            if session is not None:
                try:
                    from talentgraph.db.models import AgentRunRecord

                    rec = AgentRunRecord(
                        trace_id=run.trace_id,
                        agent=run.agent,
                        attempt=run.attempt,
                        status=run.status,
                        latency_ms=run.latency_ms,
                        quality=run.quality,
                        error_code=run.error_code,
                        started_at=run.started_at,
                    )
                    session.add(rec)
                    await session.flush()
                except Exception as db_exc:
                    log.warning("run_agent.db_persist_failed", error=str(db_exc))

            # If the result is marked failed and retryable, we could retry
            if result.status == "failed" and attempt < max_attempts:
                await asyncio.sleep(min(0.05 * (2 ** (attempt - 1)), 1.0))
                continue

            return result

        except TimeoutError:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            err = AgentError(
                agent=agent_name,
                code="timeout",
                message=f"Timeout after {timeout_s}s",
                retryable=True,
                attempt=attempt,
            )
            run = AgentRun(
                trace_id=state.trace_id,
                agent=agent_name,
                attempt=attempt,
                status="failed",
                latency_ms=latency_ms,
                error_code="timeout",
                started_at=started_at,
            )
            state.record_run(run)
            state.record_error(err)

            if attempt < max_attempts:
                await asyncio.sleep(min(0.05 * (2 ** (attempt - 1)), 1.0))
                continue

            return AgentResult(
                status="failed",
                data=None,
                quality=QualityScore(score=0.0),
                latency_ms=latency_ms,
                warnings=[err.message],
            )

        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            is_retryable = getattr(exc, "retryable", False) or isinstance(
                exc, (ConnectionError, TimeoutError)
            )
            code = getattr(exc, "code", exc.__class__.__name__)
            err = AgentError(
                agent=agent_name,
                code=str(code),
                message=str(exc),
                retryable=is_retryable,
                attempt=attempt,
            )
            run = AgentRun(
                trace_id=state.trace_id,
                agent=agent_name,
                attempt=attempt,
                status="failed",
                latency_ms=latency_ms,
                error_code=str(code),
                started_at=started_at,
            )
            state.record_run(run)
            state.record_error(err)

            if is_retryable and attempt < max_attempts:
                await asyncio.sleep(min(0.05 * (2 ** (attempt - 1)), 1.0))
                continue

            return AgentResult(
                status="failed",
                data=None,
                quality=QualityScore(score=0.0),
                latency_ms=latency_ms,
                warnings=[str(exc)],
            )

    return result or AgentResult(
        status="failed",
        data=None,
        quality=QualityScore(score=0.0),
        latency_ms=0,
        warnings=["All retry attempts failed"],
    )
