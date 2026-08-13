from typing import TypedDict, List, Dict, Any


class InvestigationState(TypedDict, total=False):
    case_id: str

    requested_agents: List[str]

    # Evidence loaded from the Knowledge Graph
    evidence: List[Dict[str, Any]]

    execution_log: List[str]

    agent_status: Dict[str, str]

    entities: List[Dict[str, Any]]
    patterns: List[Dict[str, Any]]
    leads: List[Dict[str, Any]]
    safeguarding_flags: List[Dict[str, Any]]