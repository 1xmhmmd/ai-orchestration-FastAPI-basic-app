"""
Request/response contracts for the orchestration API.

Strict Pydantic validation here is the first line of defense: it rejects
malformed input before it ever reaches an LLM call (which costs money and
latency), and `max_length` guards double as a cheap prompt-injection /
cost-control measure.
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AgentName(str, Enum):
    RESEARCHER = "researcher"
    SUMMARIZER = "summarizer"
    CRITIC = "critic"


class OrchestrationRequest(BaseModel):
    task: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="The task or question for the multi-agent pipeline to work on.",
        examples=["Summarize the pros and cons of using vector databases for RAG."],
    )
    agents: list[AgentName] = Field(
        default_factory=lambda: [
            AgentName.RESEARCHER,
            AgentName.SUMMARIZER,
            AgentName.CRITIC,
        ],
        description="Ordered pipeline of agents to run. Defaults to the full pipeline.",
    )
    max_steps: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description="Optional override for the maximum number of agent steps.",
    )

    @field_validator("task")
    @classmethod
    def _strip_and_validate(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("task must not be empty or whitespace only.")
        return v


class AgentStepResult(BaseModel):
    agent: AgentName
    output: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float


class OrchestrationResponse(BaseModel):
    task: str
    final_output: str
    steps: list[AgentStepResult]
    total_latency_ms: float
    cached: bool = False
