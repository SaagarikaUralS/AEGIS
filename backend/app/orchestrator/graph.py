from langgraph.graph import StateGraph, START, END

from app.orchestrator.state import InvestigationState

from app.agents.entity_extraction import (
    run_entity_extraction
)

from app.agents.correlation import (
    run_correlation
)

from app.agents.lead_intelligence import (
    run_lead_intelligence
)

from app.agents.victim_safeguarding import (
    run_victim_safeguarding
)


# ============================================================
# ENTITY EXTRACTION NODE
# ============================================================

def entity_extraction_node(
    state: InvestigationState
):

    print("\n[1/4] ENTITY EXTRACTION AGENT")

    entities = []

    for evidence in state["evidence"]:

        result = run_entity_extraction(
            case_id=state["case_id"],
            evidence_id=evidence["evidence_id"],
            evidence_text=evidence["evidence_text"],
        )

        entities.extend(
            result["entities"]
        )

    return {
        **state,
        "entities": entities,
    }


# ============================================================
# CORRELATION NODE
# ============================================================

def correlation_node(
    state: InvestigationState
):

    print("\n[2/4] CORRELATION & PATTERN ANALYSIS AGENT")

    result = run_correlation(
        state["case_id"]
    )

    return {
        **state,
        "patterns": result.get("patterns", []),
    }


# ============================================================
# LEAD INTELLIGENCE NODE
# ============================================================

def lead_intelligence_node(
    state: InvestigationState
):

    print("\n[3/4] LEAD INTELLIGENCE AGENT")

    result = run_lead_intelligence(
        state["case_id"]
    )

    return {
        **state,
        "leads": result.get("leads", []),
    }


# ============================================================
# VICTIM SAFEGUARDING NODE
# ============================================================

def victim_safeguarding_node(
    state: InvestigationState
):

    print("\n[4/4] VICTIM SAFEGUARDING AGENT")

    result = run_victim_safeguarding(
        state["case_id"]
    )

    return {
        **state,
        "safeguarding_flags": result.get("flags", []),
    }


# ============================================================
# BUILD GRAPH
# ============================================================

def build_investigation_graph():

    graph = StateGraph(
        InvestigationState
    )

    graph.add_node(
        "entity_extraction",
        entity_extraction_node
    )

    graph.add_node(
        "correlation",
        correlation_node
    )

    graph.add_node(
        "lead_intelligence",
        lead_intelligence_node
    )

    graph.add_node(
        "victim_safeguarding",
        victim_safeguarding_node
    )

    graph.add_edge(
        START,
        "entity_extraction"
    )

    graph.add_edge(
        "entity_extraction",
        "correlation"
    )

    graph.add_edge(
        "correlation",
        "lead_intelligence"
    )

    graph.add_edge(
        "lead_intelligence",
        "victim_safeguarding"
    )

    graph.add_edge(
        "victim_safeguarding",
        END
    )

    return graph.compile()


investigation_graph = build_investigation_graph()