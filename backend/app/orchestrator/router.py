import re
from typing import Literal

from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama


AgentName = Literal[
    "entity_extraction",
    "correlation",
    "lead_intelligence",
    "victim_safeguarding",
]


class OrchestratorDecision(BaseModel):
    agent: AgentName
    task: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float


llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
)

router_llm = llm.with_structured_output(OrchestratorDecision)


def extract_evidence_ids(command: str) -> list[str]:
    """
    Deterministically extract evidence identifiers from the command.

    Supported identifiers:
    - RAW-001
    - RAW-004
    - EVID-001
    - EVID-006
    """

    pattern = r"\b(?:RAW|EVID)-\d+\b"

    return [
        match.upper()
        for match in re.findall(pattern, command, flags=re.IGNORECASE)
    ]


def classify_command(
    command: str,
    case_id: str,
) -> OrchestratorDecision:

    evidence_ids = extract_evidence_ids(command)

    prompt = f"""
You are the task-routing component of AEGIS, an AI-assisted
digital investigation platform.

Your job is to determine which ONE specialist agent should execute
the investigator's request.

CASE ID:
{case_id}

INVESTIGATOR REQUEST:
{command}

AVAILABLE SPECIALIST AGENTS:

1. entity_extraction
Use this when the investigator wants to:
- extract entities
- identify people, accounts, devices, locations
- analyse raw evidence for entities
- analyse chats, images, metadata or other evidence
- identify mentions or relationships present directly in evidence

2. correlation
Use this when the investigator wants to:
- find connections
- correlate evidence
- identify shared accounts/devices/locations
- compare cases
- find cross-case patterns
- perform relationship or pattern analysis

3. lead_intelligence
Use this when the investigator wants to:
- generate investigative leads
- identify investigative directions
- prioritize leads
- determine what should be investigated next
- assess potential persons/entities of investigative interest

4. victim_safeguarding
Use this when the investigator wants to:
- check safeguarding concerns
- identify potential victim risks
- identify potential circulation patterns
- identify repeated victims/offenders
- flag evidence requiring safeguarding review

IMPORTANT:
- Select exactly ONE agent.
- Do not invent an agent.
- Do not perform the investigation yourself.
- Only determine which agent should handle the request.
- The case ID is already provided separately.
- Do not invent or modify evidence IDs.
- Evidence identifiers are extracted deterministically by the system.

Return:
- the selected agent
- a concise task description
- a confidence score between 0 and 1

The system will supply the evidence IDs separately.
"""

    decision = router_llm.invoke(prompt)

    # Override any LLM-generated evidence IDs with deterministic extraction.
    decision.evidence_ids = evidence_ids

    return decision