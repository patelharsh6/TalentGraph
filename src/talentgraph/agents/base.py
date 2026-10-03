"""Agent protocol and registry. `run_agent()` (retries, timeouts, AgentRun records, spans) lands in
Phase 5.1.
"""

from typing import Protocol

from talentgraph.core.schemas import AgentMessage, AgentName, AgentResult


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
