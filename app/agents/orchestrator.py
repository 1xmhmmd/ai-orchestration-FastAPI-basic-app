"""
Multi-agent orchestrator.

Runs a sequence of agents, each building on the outputs of the ones
before it, and produces a single consolidated result. Kept deliberately
simple (sequential pipeline) and readable over "clever" — the pattern
generalizes cleanly to graphs/branching later (e.g. LangGraph) without
changing the public interface consumed by the API layer.
"""

import logging
import time

from app.agents.base import BaseAgent
from app.agents.critic import CriticAgent
from app.agents.researcher import ResearcherAgent
from app.agents.summarizer import SummarizerAgent
from app.core.config import Settings
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentName, AgentStepResult, OrchestrationResponse
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, llm_client: LLMClient, settings: Settings):
        self._settings = settings
        self._registry: dict[AgentName, BaseAgent] = {
            AgentName.RESEARCHER: ResearcherAgent(llm_client),
            AgentName.SUMMARIZER: SummarizerAgent(llm_client),
            AgentName.CRITIC: CriticAgent(llm_client),
        }

    async def run(
        self, task: str, agent_names: list[AgentName], max_steps: int | None
    ) -> OrchestrationResponse:
        step_limit = min(max_steps or self._settings.MAX_AGENT_STEPS, len(agent_names))
        pipeline = agent_names[:step_limit]

        steps: list[AgentStepResult] = []
        start = time.perf_counter()

        for agent_name in pipeline:
            agent = self._registry.get(agent_name)
            if agent is None:
                raise AgentExecutionError(f"Unknown agent: {agent_name}")
            try:
                result = await agent.run(task, steps)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Agent '%s' failed", agent_name)
                raise AgentExecutionError(
                    f"Agent '{agent_name.value}' failed to complete its step."
                ) from exc
            steps.append(result)

        total_latency_ms = (time.perf_counter() - start) * 1000
        final_output = steps[-1].output if steps else ""

        return OrchestrationResponse(
            task=task,
            final_output=final_output,
            steps=steps,
            total_latency_ms=round(total_latency_ms, 2),
            cached=False,
        )
