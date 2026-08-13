from app.knowledge_graph.neo4j_client import neo4j_client
from app.orchestrator.graph import investigation_graph
from app.services.execution_service import (
    create_execution,
    start_agent_execution,
    complete_agent_execution,
    fail_agent_execution,
    complete_execution,
)

# ============================================================
# LOAD RAW EVIDENCE
# ============================================================

GET_CASE_EVIDENCE = """
MATCH (c:Case {case_id: $case_id})
      -[:HAS_EVIDENCE]->
      (e:Evidence)
WHERE e.type = 'raw_text'
RETURN
    e.evidence_id AS evidence_id,
    e.description AS evidence_text
ORDER BY e.evidence_id
"""


def load_case_evidence(case_id: str):
    return neo4j_client.run_query(
        GET_CASE_EVIDENCE,
        {"case_id": case_id},
    )


# ============================================================
# RUN INVESTIGATION
# ============================================================

def run_investigation(
    case_id: str,
    requested_agents: list[str],
):

    evidence = load_case_evidence(case_id)

    # --------------------------------------------------------
    # Create execution record
    # --------------------------------------------------------

    execution_id = create_execution(
        case_id
    )

    initial_state = {
        "case_id": case_id,
        "requested_agents": requested_agents,

        "evidence": evidence,

        "execution_log": [],

        "agent_status": {
            "entity_extraction": "NOT_REQUESTED",
            "correlation": "NOT_REQUESTED",
            "lead_intelligence": "NOT_REQUESTED",
            "victim_safeguarding": "NOT_REQUESTED",
        },

        "entities": [],
        "patterns": [],
        "leads": [],
        "safeguarding_flags": [],
    }

    print("\n" + "=" * 60)
    print("AEGIS MODULAR INVESTIGATION")
    print("=" * 60)

    print(f"Execution: {execution_id}")
    print(f"Case: {case_id}")
    print(f"Requested agents: {requested_agents}")

    final_state = initial_state

    # --------------------------------------------------------
    # Execute selected agents independently
    # --------------------------------------------------------

    for agent in requested_agents:

        print("\n" + "-" * 60)
        print(f"ORCHESTRATOR → {agent}")
        print("-" * 60)

        start_agent_execution(
            execution_id=execution_id,
            agent_id=agent,
        )

        try:

            agent_state = {
                **final_state,
                "requested_agents": [agent],
            }

            result = investigation_graph.invoke(
                agent_state
            )

            final_state = {
                **final_state,
                **result,
            }

            final_state["agent_status"] = {
                **final_state["agent_status"],
                agent: "COMPLETED",
            }

            final_state["execution_log"] = [
                *final_state["execution_log"],
                f"{agent}: COMPLETED",
            ]

            complete_agent_execution(
                execution_id=execution_id,
                agent_id=agent,
            )

        except Exception as error:

            print(
                f"\n[ERROR] {agent}: {error}"
            )

            fail_agent_execution(
                execution_id=execution_id,
                agent_id=agent,
                error=str(error),
            )

            final_state["agent_status"] = {
                **final_state["agent_status"],
                agent: "FAILED",
            }

            final_state["execution_log"] = [
                *final_state["execution_log"],
                f"{agent}: FAILED",
            ]

    # --------------------------------------------------------
    # Determine final execution status
    # --------------------------------------------------------

    failed_agents = [
        agent
        for agent, status
        in final_state["agent_status"].items()
        if status == "FAILED"
    ]

    if failed_agents:
        execution_status = "PARTIAL_FAILURE"
    else:
        execution_status = "COMPLETED"

    complete_execution(
        execution_id=execution_id,
        status=execution_status,
    )

    print("\n" + "=" * 60)
    print("INVESTIGATION COMPLETE")
    print("=" * 60)

    print(
        f"Execution status: {execution_status}"
    )

    for log in final_state["execution_log"]:
        print("✓", log)

    return {
        **final_state,
        "execution_id": execution_id,
        "execution_status": execution_status,
    }