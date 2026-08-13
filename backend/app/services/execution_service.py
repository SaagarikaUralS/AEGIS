import uuid
from datetime import datetime, timezone

from app.knowledge_graph.neo4j_client import neo4j_client


# ============================================================
# CREATE EXECUTION
# ============================================================

CREATE_EXECUTION = """
MATCH (c:Case {case_id: $case_id})

CREATE (e:Execution {
    execution_id: $execution_id,
    case_id: $case_id,
    status: 'RUNNING',
    started_at: $started_at
})

CREATE (c)-[:HAS_EXECUTION]->(e)

RETURN e.execution_id AS execution_id
"""


def create_execution(case_id: str) -> str:

    execution_id = (
        f"EXEC-{uuid.uuid4().hex[:10]}"
    )

    started_at = datetime.now(
        timezone.utc
    ).isoformat()

    neo4j_client.run_query(
        CREATE_EXECUTION,
        {
            "case_id": case_id,
            "execution_id": execution_id,
            "started_at": started_at,
        },
    )

    return execution_id


# ============================================================
# CREATE AGENT EXECUTION
# ============================================================

CREATE_AGENT_EXECUTION = """
MATCH (e:Execution {
    execution_id: $execution_id
})

CREATE (a:AgentExecution {
    execution_id: $execution_id,
    agent_id: $agent_id,
    status: 'RUNNING',
    started_at: $started_at
})

CREATE (e)-[:RUNS_AGENT]->(a)

RETURN a
"""


def start_agent_execution(
    execution_id: str,
    agent_id: str,
):

    started_at = datetime.now(
        timezone.utc
    ).isoformat()

    neo4j_client.run_query(
        CREATE_AGENT_EXECUTION,
        {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "started_at": started_at,
        },
    )


# ============================================================
# COMPLETE AGENT
# ============================================================

COMPLETE_AGENT_EXECUTION = """
MATCH (a:AgentExecution {
    execution_id: $execution_id,
    agent_id: $agent_id
})

SET a.status = 'COMPLETED',
    a.completed_at = $completed_at

RETURN a
"""


def complete_agent_execution(
    execution_id: str,
    agent_id: str,
):

    completed_at = datetime.now(
        timezone.utc
    ).isoformat()

    neo4j_client.run_query(
        COMPLETE_AGENT_EXECUTION,
        {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "completed_at": completed_at,
        },
    )


# ============================================================
# FAIL AGENT
# ============================================================

FAIL_AGENT_EXECUTION = """
MATCH (a:AgentExecution {
    execution_id: $execution_id,
    agent_id: $agent_id
})

SET a.status = 'FAILED',
    a.completed_at = $completed_at,
    a.error = $error

RETURN a
"""


def fail_agent_execution(
    execution_id: str,
    agent_id: str,
    error: str,
):

    completed_at = datetime.now(
        timezone.utc
    ).isoformat()

    neo4j_client.run_query(
        FAIL_AGENT_EXECUTION,
        {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "completed_at": completed_at,
            "error": error,
        },
    )


# ============================================================
# COMPLETE INVESTIGATION
# ============================================================

COMPLETE_EXECUTION = """
MATCH (e:Execution {
    execution_id: $execution_id
})

SET e.status = $status,
    e.completed_at = $completed_at

RETURN e
"""


def complete_execution(
    execution_id: str,
    status: str = "COMPLETED",
):

    completed_at = datetime.now(
        timezone.utc
    ).isoformat()

    neo4j_client.run_query(
        COMPLETE_EXECUTION,
        {
            "execution_id": execution_id,
            "status": status,
            "completed_at": completed_at,
        },
    )