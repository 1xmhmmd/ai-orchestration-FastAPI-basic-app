from app.agents.base import BaseAgent
from app.schemas.agent import AgentName, AgentStepResult


class CriticAgent(BaseAgent):
    name = AgentName.CRITIC
    system_prompt = (
        "You are a rigorous critic and editor. Review the draft answer for factual "
        "gaps, unclear reasoning, or missed edge cases relative to the original task. "
        "Return an improved final version of the answer — not a list of critiques. "
        "If the draft is already correct and clear, return it with only minor polish."
    )

    def build_user_prompt(self, task: str, prior_outputs: list[AgentStepResult]) -> str:
        draft = next(
            (step.output for step in reversed(prior_outputs) if step.agent == AgentName.SUMMARIZER),
            prior_outputs[-1].output if prior_outputs else "",
        )
        return (
            f"Original task:\n{task}\n\nDraft answer to review and improve:\n{draft}\n\n"
            "Return only the final, improved answer."
        )
