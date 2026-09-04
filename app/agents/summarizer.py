from app.agents.base import BaseAgent
from app.schemas.agent import AgentName, AgentStepResult


class SummarizerAgent(BaseAgent):
    name = AgentName.SUMMARIZER
    system_prompt = (
        "You are a clear, precise writing agent. Using the task and any research "
        "notes provided, produce a well-organized, direct answer to the task. "
        "Avoid filler; write for a technical, time-constrained reader."
    )

    def build_user_prompt(self, task: str, prior_outputs: list[AgentStepResult]) -> str:
        context = "\n\n".join(
            f"[{step.agent.value} notes]\n{step.output}" for step in prior_outputs
        )
        context_block = f"\n\nContext from prior agents:\n{context}" if context else ""
        return f"Task:\n{task}{context_block}\n\nWrite the final answer now."
