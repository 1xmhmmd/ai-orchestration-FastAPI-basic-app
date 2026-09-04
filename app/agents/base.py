"""
Agent abstraction.

Every agent is a small, focused, single-responsibility unit that takes
the running context (original task + prior agents' outputs) and produces
one contribution. The orchestrator composes them into a pipeline. This
keeps each agent independently testable (mock `LLMClient`, assert on
prompt construction and output parsing) and easy to extend — adding a
new agent means adding one class, not touching orchestration logic.
"""

import time
from abc import ABC, abstractmethod

from app.schemas.agent import AgentName, AgentStepResult
from app.services.llm_client import LLMClient


class BaseAgent(ABC):
    name: AgentName
    system_prompt: str

    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    @abstractmethod
    def build_user_prompt(self, task: str, prior_outputs: list[AgentStepResult]) -> str:
        """Construct this agent's prompt from the task and prior context."""

    async def run(self, task: str, prior_outputs: list[AgentStepResult]) -> AgentStepResult:
        start = time.perf_counter()
        user_prompt = self.build_user_prompt(task, prior_outputs)
        result = await self._llm.complete(system_prompt=self.system_prompt, user_prompt=user_prompt)
        latency_ms = (time.perf_counter() - start) * 1000

        return AgentStepResult(
            agent=self.name,
            output=result.text.strip(),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=round(latency_ms, 2),
        )
