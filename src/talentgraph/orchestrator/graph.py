"""Step 4.7: LangGraph pipeline with degradation edges (run_parse_pipeline, run_match_pipeline)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog
from langgraph.graph import END, START, StateGraph

from talentgraph.agents.base import run_agent
from talentgraph.agents.matching.agent import MatchingAgent
from talentgraph.agents.matching.blind import redact_resume, redact_skill_profile
from talentgraph.agents.normalization.agent import NormalizationAgent
from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.core.schemas.messages import AgentError, AgentMessage, AgentResult
from talentgraph.core.schemas.resume import ParsedResume
from talentgraph.core.schemas.skills import SkillProfile
from talentgraph.orchestrator.state import PipelineState

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


def create_pipeline_graph(
    parser: ParsingAgent | None = None,
    normalizer: NormalizationAgent | None = None,
    matcher: MatchingAgent | None = None,
    session: AsyncSession | None = None,
) -> Any:
    """Build the LangGraph state machine with graceful degradation edges (plan §4.2)."""
    p_agent = parser or ParsingAgent()
    n_agent = normalizer or NormalizationAgent()
    m_agent = matcher or MatchingAgent()

    builder = StateGraph(PipelineState)

    async def parse_step(state: PipelineState) -> dict[str, Any]:
        """Parse raw file bytes if parsed_resume is not already present."""
        if state.parsed_resume is not None:
            return {}

        if not state.file_bytes:
            state.record_error(
                AgentError(
                    agent="parser",
                    code="missing_input",
                    message="No file bytes or parsed resume provided",
                    retryable=False,
                )
            )
            return {"status": "failed"}

        filename = state.input_meta.get("filename", "resume.txt")

        async def _call_parser() -> AgentResult:
            t0 = time.perf_counter()
            parsed_res = await p_agent.parse(state.file_bytes, filename=filename)  # type: ignore[arg-type]
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if parsed_res.warnings:
                for w in parsed_res.warnings:
                    state.record_error(
                        AgentError(
                            agent="parser",
                            code="quota_exceeded" if "quota" in w.lower() else "parser_warning",
                            message=w,
                            retryable=False,
                        )
                    )
            return AgentResult(
                status=parsed_res.status,  # "ok" or "partial"
                data={
                    "parsed_resume": parsed_res.resume.model_dump(),
                    "warnings": parsed_res.warnings,
                },
                quality=parsed_res.quality,
                latency_ms=latency_ms,
            )

        res = await run_agent("parser", _call_parser, state, session=session)
        if res.status == "failed":
            return {"status": "failed", "errors": state.errors, "agent_runs": state.agent_runs}

        resume_data = res.data.get("parsed_resume") if res.data else None
        if resume_data:
            return {
                "parsed_resume": ParsedResume.model_validate(resume_data),
                "status": "partial" if res.status == "partial" else state.status,
                "errors": state.errors,
                "agent_runs": state.agent_runs,
            }
        return {"status": "failed", "errors": state.errors, "agent_runs": state.agent_runs}

    async def normalize_step(state: PipelineState) -> dict[str, Any]:
        """Normalize parsed resume into canonical SkillProfile; degrade to raw_skills on failure."""
        if state.status == "failed" or state.parsed_resume is None:
            return {}
        if state.skill_profile is not None:
            return {}

        resume = state.parsed_resume
        raw_skills = [s.raw for s in resume.skills if s.raw]

        async def _call_normalizer() -> AgentResult:
            msg = AgentMessage(
                trace_id=state.trace_id,
                sender="orchestrator",
                recipient="normalizer",
                type="task",
                payload={"resume": resume.model_dump()},
            )
            return await n_agent.handle(msg)

        res = await run_agent("normalizer", _call_normalizer, state, session=session)
        if res.status == "failed" or not res.data:
            state.record_error(
                AgentError(
                    agent="normalizer",
                    code="normalization_failed",
                    message="Normalizer failed; retaining raw skill strings",
                    retryable=False,
                )
            )
            return {
                "raw_skills": raw_skills,
                "status": "partial",
                "errors": state.errors,
                "agent_runs": state.agent_runs,
            }

        profile = SkillProfile.model_validate(res.data)
        return {
            "skill_profile": profile,
            "raw_skills": raw_skills,
            "status": "partial" if res.status == "partial" else state.status,
            "errors": state.errors,
            "agent_runs": state.agent_runs,
        }

    async def redact_step(state: PipelineState) -> dict[str, Any]:
        """Apply blind screening redactions if blind=True (F4)."""
        updates: dict[str, Any] = {}
        if state.skill_profile is not None:
            updates["skill_profile"] = redact_skill_profile(state.skill_profile)
        if state.parsed_resume is not None:
            updates["parsed_resume"] = redact_resume(state.parsed_resume)
        return updates

    async def match_step(state: PipelineState) -> dict[str, Any]:
        """Match candidate profile against job requirements; degrade if matcher fails."""
        if state.job is None or state.skill_profile is None:
            return {}

        profile = state.skill_profile
        job = state.job
        threshold = state.threshold

        async def _call_matcher() -> AgentResult:
            job_payload = job.model_dump() if hasattr(job, "model_dump") else job
            msg = AgentMessage(
                trace_id=state.trace_id,
                sender="orchestrator",
                recipient="matcher",
                type="task",
                payload={
                    "profile": profile.model_dump(),
                    "job": job_payload,
                    "threshold": threshold,
                },
            )
            return await m_agent.handle(msg)

        res = await run_agent("matcher", _call_matcher, state, session=session)
        if res.status == "failed" or not res.data:
            state.record_error(
                AgentError(
                    agent="matcher",
                    code="matching_failed",
                    message="Matcher failed; profile kept without match result",
                    retryable=False,
                )
            )
            return {
                "match_result": None,
                "status": "partial",
                "errors": state.errors,
                "agent_runs": state.agent_runs,
            }

        from talentgraph.core.schemas.matching import MatchResult

        result = MatchResult.model_validate(res.data)
        return {
            "match_result": result,
            "status": "partial" if res.status == "partial" else state.status,
            "errors": state.errors,
            "agent_runs": state.agent_runs,
        }

    async def persist_step(state: PipelineState) -> dict[str, Any]:
        """Terminal persistence node for DB saves if session is provided."""
        return {}

    # Define nodes
    builder.add_node("parse", parse_step)
    builder.add_node("normalize", normalize_step)
    builder.add_node("redact", redact_step)
    builder.add_node("match", match_step)
    builder.add_node("persist", persist_step)

    # Edge from START to parse
    builder.add_edge(START, "parse")

    # Conditional branch after parse
    def route_after_parse(state: PipelineState) -> str:
        if state.status == "failed":
            return END
        return "normalize"

    builder.add_conditional_edges("parse", route_after_parse, ["normalize", END])

    # Conditional branch after normalize
    def route_after_normalize(state: PipelineState) -> str:
        if state.job is not None and state.skill_profile is not None:
            if state.blind:
                return "redact"
            return "match"
        return "persist"

    builder.add_conditional_edges(
        "normalize", route_after_normalize, ["redact", "match", "persist"]
    )

    # Redact unconditionally flows to match
    builder.add_edge("redact", "match")

    # Match flows to persist
    builder.add_edge("match", "persist")

    # Persist flows to END
    builder.add_edge("persist", END)

    return builder.compile()


async def run_parse_pipeline(
    input_state: PipelineState,
    *,
    parser: ParsingAgent | None = None,
    normalizer: NormalizationAgent | None = None,
    session: AsyncSession | None = None,
) -> PipelineState:
    """Run parse and normalization pipeline."""
    graph = create_pipeline_graph(parser=parser, normalizer=normalizer, session=session)
    result_dict = await graph.ainvoke(input_state)
    return PipelineState.model_validate(result_dict)


async def run_match_pipeline(
    input_state: PipelineState,
    *,
    parser: ParsingAgent | None = None,
    normalizer: NormalizationAgent | None = None,
    matcher: MatchingAgent | None = None,
    session: AsyncSession | None = None,
) -> PipelineState:
    """Run complete pipeline through parsing, normalization, blind redaction, and matching."""
    graph = create_pipeline_graph(
        parser=parser, normalizer=normalizer, matcher=matcher, session=session
    )
    result_dict = await graph.ainvoke(input_state)
    return PipelineState.model_validate(result_dict)
