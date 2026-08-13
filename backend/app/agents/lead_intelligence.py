from typing import TypedDict, List, Dict, Any

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.knowledge_graph.neo4j_client import neo4j_client


# ============================================================
# STRUCTURED OUTPUT
# ============================================================

class Lead(BaseModel):
    subject: str = Field(
        description="Entity associated with the investigative lead"
    )

    priority: str = Field(
        description="Priority level: HIGH, MEDIUM, or LOW"
    )

    confidence: float = Field(
        description="Confidence score between 0 and 1"
    )

    reason: str = Field(
        description="Why this finding deserves investigative attention"
    )

    recommended_direction: str = Field(
        description="A suggested investigative direction"
    )


class LeadGenerationResult(BaseModel):
    leads: List[Lead]


# ============================================================
# LANGGRAPH STATE
# ============================================================

class LeadIntelligenceState(TypedDict):
    case_id: str
    findings: List[Dict[str, Any]]
    leads: List[Dict[str, Any]]
    status: str


# ============================================================
# LOCAL LLM
# ============================================================

llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
)

structured_llm = llm.with_structured_output(
    LeadGenerationResult
)


# ============================================================
# PROMPT
# ============================================================

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are the Lead Intelligence Agent in AEGIS,
an AI-assisted child protection investigation platform.

Your role is to convert existing analytical findings into
prioritized investigative leads.

IMPORTANT:

You are NOT determining guilt.

You are NOT identifying someone as a criminal.

You are NOT making final investigative decisions.

You are assisting a human investigator.

Use ONLY the information contained in the supplied findings.

For each lead provide:

1. subject
2. priority
3. confidence
4. reason
5. recommended_direction

Priority rules:

HIGH:
The finding represents a strong or repeated cross-case
connection that should receive immediate investigative
attention.

MEDIUM:
The finding represents a potentially useful connection
but requires additional verification.

LOW:
The finding is weak or contextual and may be useful later.

Confidence must be between 0 and 1.

Recommended directions must be investigative suggestions,
not conclusions.

For example:

Finding:
"Account beta_synthetic appears in multiple cases:
CASE-001, CASE-002."

Possible lead:

Subject:
beta_synthetic

Priority:
HIGH

Reason:
"The same account appears across multiple independent
case records."

Recommended direction:
"Review account activity and associated devices across
the linked cases."
""",
        ),
        (
            "human",
            """
Case ID:
{case_id}

Existing analytical findings:

{findings}
""",
        ),
    ]
)


# ============================================================
# FETCH FINDINGS FROM KNOWLEDGE GRAPH
# ============================================================

GET_CASE_FINDINGS = """
MATCH (c:Case {case_id: $case_id})-[:HAS_FINDING]->(f:Finding)

RETURN
    f.finding_id AS finding_id,
    f.type AS type,
    f.description AS description
ORDER BY f.finding_id
"""


def get_findings(case_id: str):

    return neo4j_client.run_query(
        GET_CASE_FINDINGS,
        {
            "case_id": case_id
        }
    )


# ============================================================
# GENERATE LEADS
# ============================================================

def generate_leads(state: LeadIntelligenceState):

    findings_text = "\n".join(
        [
            f"- [{finding['type']}] {finding['description']}"
            for finding in state["findings"]
        ]
    )

    if not findings_text:

        print("\nNo findings available for lead generation.")

        return {
            **state,
            "leads": [],
            "status": "COMPLETED",
        }

    chain = prompt | structured_llm

    result = chain.invoke(
        {
            "case_id": state["case_id"],
            "findings": findings_text,
        }
    )

    leads = [
        lead.model_dump()
        for lead in result.leads
    ]

    print("\nLEAD INTELLIGENCE")
    print("==============================")

    for lead in leads:

        print(
            f"[{lead['priority']}] "
            f"{lead['subject']} "
            f"(confidence={lead['confidence']})"
        )

        print(
            f"Reason: {lead['reason']}"
        )

        print(
            f"Direction: "
            f"{lead['recommended_direction']}"
        )

        print("------------------------------")

    return {
        **state,
        "leads": leads,
        "status": "COMPLETED",
    }


# ============================================================
# WRITE LEADS TO KNOWLEDGE GRAPH
# ============================================================

def write_leads_to_graph(state: LeadIntelligenceState):

    for index, lead in enumerate(
        state["leads"],
        start=1
    ):

        lead_id = (
            f"{state['case_id']}-LEAD-{index:03d}"
        )

        query = """
        MERGE (l:Lead {
            lead_id: $lead_id
        })

        SET
            l.subject = $subject,
            l.priority = $priority,
            l.confidence = $confidence,
            l.reason = $reason,
            l.recommended_direction = $recommended_direction,
            l.status = 'NEW'

        WITH l

        MATCH (c:Case {
            case_id: $case_id
        })

        MERGE (c)-[:HAS_LEAD]->(l)
        """

        neo4j_client.run_query(
            query,
            {
                "lead_id": lead_id,
                "subject": lead["subject"],
                "priority": lead["priority"],
                "confidence": lead["confidence"],
                "reason": lead["reason"],
                "recommended_direction": lead[
                    "recommended_direction"
                ],
                "case_id": state["case_id"],
            },
        )

    print("\nLeads successfully written to Neo4j.")

    return state


# ============================================================
# PUBLIC AGENT FUNCTION
# ============================================================

def run_lead_intelligence(case_id: str):

    findings = get_findings(case_id)

    initial_state: LeadIntelligenceState = {
        "case_id": case_id,
        "findings": findings,
        "leads": [],
        "status": "RUNNING",
    }

    state = generate_leads(
        initial_state
    )

    state = write_leads_to_graph(
        state
    )

    return state