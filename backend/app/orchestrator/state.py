from typing import TypedDict, Any


class InvestigationState(TypedDict, total=False):
    case_id: str
    command: str

    selected_agent: str
    task: str
    evidence_ids: list[str]
    routing_confidence: float

    evidence: list[dict[str, Any]]

    entities: list[dict[str, Any]]
    patterns: list[dict[str, Any]]
    leads: list[dict[str, Any]]
    safeguarding_flags: list[dict[str, Any]]

    result: dict[str, Any]