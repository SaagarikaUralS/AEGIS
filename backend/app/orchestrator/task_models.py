from typing import Literal
from pydantic import BaseModel, Field


AgentId = Literal[
    "entity_extraction",
    "correlation",
    "lead_intelligence",
    "victim_safeguarding",
]

TaskStatus = Literal[
    "WAITING",
    "READY",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "BLOCKED",
    "HUMAN_REVIEW",
]


class InvestigationTask(BaseModel):
    task_id: str
    case_id: str

    agent_id: AgentId
    description: str

    evidence_ids: list[str] = Field(default_factory=list)

    status: TaskStatus = "READY"

    priority: int = 5

    attempts: int = 0
    max_retries: int = 2

    depends_on: list[str] = Field(default_factory=list)

    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None

    error: str | None = None