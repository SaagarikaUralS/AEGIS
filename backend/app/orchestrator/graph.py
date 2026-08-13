from langgraph.graph import StateGraph, START, END

from app.orchestrator.state import InvestigationState

from app.agents.entity_extraction import run_entity_extraction
from app.agents.correlation import run_correlation
from app.agents.lead_intelligence import run_lead_intelligence
from app.agents.victim_safeguarding import run_victim_safeguarding


def entity_extraction_node(state: InvestigationState):
    case_id = state["case_id"]
    evidence_ids = state.get("evidence_ids", [])

    if not evidence_ids:
        return {
            "result": {
                "agent": "entity_extraction",
                "status": "FAILED",
                "message": "Entity extraction requires an evidence ID."
            }
        }

    evidence = state.get("evidence", [])

    evidence_map = {
        item.get("evidence_id"): item
        for item in evidence
    }

    outputs = []

    for evidence_id in evidence_ids:
        item = evidence_map.get(evidence_id)

        if not item:
            continue

        evidence_text = (
            item.get("evidence_text")
            or item.get("description")
            or item.get("text")
            or ""
        )

        result = run_entity_extraction(
            case_id=case_id,
            evidence_id=evidence_id,
            evidence_text=evidence_text,
        )

        outputs.append({
            "evidence_id": evidence_id,
            "result": result,
        })

    return {
        "result": {
            "agent": "entity_extraction",
            "status": "COMPLETED",
            "outputs": outputs,
        }
    }


def correlation_node(state: InvestigationState):

    case_id = state["case_id"]

    result = run_correlation(case_id)

    return {
        "result": {
            "agent": "correlation",
            "status": "COMPLETED",
            "outputs": result,
        }
    }


def lead_intelligence_node(state: InvestigationState):

    case_id = state["case_id"]

    result = run_lead_intelligence(case_id)

    return {
        "result": {
            "agent": "lead_intelligence",
            "status": "COMPLETED",
            "outputs": result,
        }
    }


def victim_safeguarding_node(state: InvestigationState):

    case_id = state["case_id"]

    result = run_victim_safeguarding(case_id)

    return {
        "result": {
            "agent": "victim_safeguarding",
            "status": "COMPLETED",
            "outputs": result,
        }
    }


def route_agent(state: InvestigationState):

    return state["selected_agent"]


builder = StateGraph(InvestigationState)

builder.add_node(
    "entity_extraction",
    entity_extraction_node,
)

builder.add_node(
    "correlation",
    correlation_node,
)

builder.add_node(
    "lead_intelligence",
    lead_intelligence_node,
)

builder.add_node(
    "victim_safeguarding",
    victim_safeguarding_node,
)


builder.add_conditional_edges(
    START,
    route_agent,
    {
        "entity_extraction": "entity_extraction",
        "correlation": "correlation",
        "lead_intelligence": "lead_intelligence",
        "victim_safeguarding": "victim_safeguarding",
    },
)


builder.add_edge("entity_extraction", END)
builder.add_edge("correlation", END)
builder.add_edge("lead_intelligence", END)
builder.add_edge("victim_safeguarding", END)


investigation_graph = builder.compile()