from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.agents.entity_extraction import (
    run_entity_extraction,
)

from app.agents.correlation import (
    run_correlation,
)

from app.agents.lead_intelligence import (
    run_lead_intelligence,
)

from app.agents.victim_safeguarding import (
    run_victim_safeguarding,
)

from app.knowledge_graph.neo4j_client import neo4j_client


class TaskState(TypedDict, total=False):

    task_id: str
    case_id: str
    agent_id: str

    description: str
    evidence_ids: list[str]

    result: dict


def execute_entity(state: TaskState):

    case_id = state["case_id"]

    evidence_ids = state.get(
        "evidence_ids",
        [],
    )

    results = []

    if evidence_ids:

        for evidence_id in evidence_ids:

            query = """
            MATCH (r:RawEvidence {
                evidence_id: $evidence_id
            })

            RETURN
                r.evidence_id AS evidence_id,
                r.description AS evidence_text
            """

            rows = neo4j_client.run_query(
                query,
                {
                    "evidence_id": evidence_id
                },
            )

            if not rows:
                raise ValueError(
                    f"Evidence {evidence_id} not found"
                )

            evidence = rows[0]

            result = run_entity_extraction(
                case_id=case_id,
                evidence_id=evidence_id,
                evidence_text=evidence["evidence_text"],
            )

            results.append(result)

    else:

        query = """
        MATCH (r:RawEvidence {
            case_id: $case_id
        })

        RETURN
            r.evidence_id AS evidence_id,
            r.description AS evidence_text
        """

        rows = neo4j_client.run_query(
            query,
            {"case_id": case_id},
        )

        for evidence in rows:

            result = run_entity_extraction(
                case_id=case_id,
                evidence_id=evidence["evidence_id"],
                evidence_text=evidence["evidence_text"],
            )

            results.append(result)

    return {
        "result": {
            "agent": "entity_extraction",
            "results": results,
        }
    }


def execute_correlation(state: TaskState):

    result = run_correlation(
        state["case_id"]
    )

    return {
        "result": result
    }


def execute_lead(state: TaskState):

    result = run_lead_intelligence(
        state["case_id"]
    )

    return {
        "result": result
    }


def execute_safeguarding(state: TaskState):

    result = run_victim_safeguarding(
        state["case_id"]
    )

    return {
        "result": result
    }


def build_task_graph():

    graph = StateGraph(TaskState)

    graph.add_node(
        "entity_extraction",
        execute_entity,
    )

    graph.add_node(
        "correlation",
        execute_correlation,
    )

    graph.add_node(
        "lead_intelligence",
        execute_lead,
    )

    graph.add_node(
        "victim_safeguarding",
        execute_safeguarding,
    )

    def route_task(state: TaskState):

        return state["agent_id"]

    graph.add_conditional_edges(
        START,
        route_task,
        {
            "entity_extraction":
                "entity_extraction",

            "correlation":
                "correlation",

            "lead_intelligence":
                "lead_intelligence",

            "victim_safeguarding":
                "victim_safeguarding",
        },
    )

    graph.add_edge(
        "entity_extraction",
        END,
    )

    graph.add_edge(
        "correlation",
        END,
    )

    graph.add_edge(
        "lead_intelligence",
        END,
    )

    graph.add_edge(
        "victim_safeguarding",
        END,
    )

    return graph.compile()


task_graph = build_task_graph()


def execute_task(task):

    state = {
        "task_id": task["task_id"],
        "case_id": task["case_id"],
        "agent_id": task["agent_id"],
        "description": task["description"],
        "evidence_ids": task.get(
            "evidence_ids",
            [],
        ),
    }

    return task_graph.invoke(state)