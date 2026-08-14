from datetime import datetime, timezone

from app.orchestrator.router import classify_command
from app.orchestrator.graph import investigation_graph
from app.knowledge_graph.neo4j_client import neo4j_client

from app.services.execution_service import (
    create_execution,
    start_agent_execution,
    complete_agent_execution,
    fail_agent_execution,
    complete_execution,
)

GET_EVIDENCE_BY_ID = """
MATCH (e)
WHERE (e:Evidence OR e:RawEvidence)
  AND e.evidence_id = $evidence_id
  AND e.case_id = $case_id

RETURN
    e.evidence_id AS evidence_id,
    e.case_id AS case_id,
    coalesce(e.description, "") AS description,
    CASE
        WHEN e:RawEvidence THEN "raw"
        ELSE "structured"
    END AS evidence_type
"""


GET_ALL_CASE_EVIDENCE = """
MATCH (e)
WHERE (e:Evidence OR e:RawEvidence)
  AND e.case_id = $case_id

RETURN
    e.evidence_id AS evidence_id,
    e.case_id AS case_id,
    coalesce(e.description, "") AS description,
    CASE
        WHEN e:RawEvidence THEN "raw"
        ELSE "structured"
    END AS evidence_type

ORDER BY e.evidence_id
"""


def get_evidence(case_id: str, evidence_ids: list[str]):

    if evidence_ids:

        rows = []

        for evidence_id in evidence_ids:

            result = neo4j_client.run_query(
                GET_EVIDENCE_BY_ID,
                {
                    "evidence_id": evidence_id,
                    "case_id": case_id,
                },
            )

            if result:
                rows.extend(result)

        return rows

    return neo4j_client.run_query(
        GET_ALL_CASE_EVIDENCE,
        {
            "case_id": case_id,
        },
    )


def run_orchestrated_command(
    case_id: str,
    command: str,
):

    decision = classify_command(
        command=command,
        case_id=case_id,
    )

    selected_agent = decision.agent

    execution_id = create_execution(case_id)

    agent_started = False

    try:

        start_agent_execution(
            execution_id=execution_id,
            agent_id=selected_agent,
        )

        agent_started = True

        evidence = get_evidence(
            case_id=case_id,
            evidence_ids=decision.evidence_ids,
        )

        initial_state = {
            "case_id": case_id,
            "command": command,
            "selected_agent": selected_agent,
            "task": decision.task,
            "evidence_ids": decision.evidence_ids,
            "routing_confidence": decision.confidence,
            "evidence": evidence,
        }

        final_state = investigation_graph.invoke(
            initial_state
        )

        if agent_started:

            complete_agent_execution(
                execution_id=execution_id,
                agent_id=selected_agent,
            )

        complete_execution(
            execution_id=execution_id,
            status="COMPLETED",
        )

        return {
            "system": "AEGIS",
            "status": "COMPLETED",

            "execution_id": execution_id,

            "case_id": case_id,

            "command": command,

            "routing": {
                "agent": selected_agent,
                "task": decision.task,
                "evidence_ids": decision.evidence_ids,
                "confidence": decision.confidence,
            },

            "agent_status": {
                selected_agent: "COMPLETED",
            },

            "result": final_state.get(
                "result",
                {}
            ),
        }

    except Exception as error:

        if agent_started:

            fail_agent_execution(
                execution_id=execution_id,
                agent_id=selected_agent,
                error=str(error),
            )

        complete_execution(
            execution_id=execution_id,
            status="PARTIAL_FAILURE",
        )

        raise