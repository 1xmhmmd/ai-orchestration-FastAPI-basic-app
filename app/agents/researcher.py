from app.agents.base import BaseAgent
from app.schemas.agent import AgentName, AgentStepResult


class ResearcherAgent(BaseAgent):
    name = AgentName.RESEARCHER
    system_prompt = (
        "You are a meticulous research agent. Given a task, identify the key facts, "
        "considerations, and relevant context needed to address it thoroughly. "
        "Be concise and structure your findings as short bullet points. "
        "Do not answer the task yet — only gather and lay out the groundwork."
    )

    def build_user_prompt(self, task: str, prior_outputs: list[AgentStepResult]) -> str:
        return f"Task:\n{task}\n\nList the key research points needed to address this task."
