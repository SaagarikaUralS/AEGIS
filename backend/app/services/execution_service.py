from datetime import datetime, timezone
from uuid import uuid4

from app.knowledge_graph.neo4j_client import neo4j_client


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def create_execution(case_id: str, task_id: str | None = None):
    execution_id = f"EXEC-{uuid4().hex[:8].upper()}"
    created_at = now_iso()

    query = """
    MATCH (c:Case {case_id: $case_id})

    CREATE (e:Execution {
        execution_id: $execution_id,
        case_id: $case_id,
        status: 'RUNNING',
        created_at: $created_at
    })

    CREATE (c)-[:HAS_EXECUTION]->(e)

    WITH e

    OPTIONAL MATCH (t:InvestigationTask {
        task_id: $task_id
    })

    FOREACH (_ IN CASE
        WHEN t IS NOT NULL THEN [1]
        ELSE []
    END |
        CREATE (e)-[:EXECUTES_TASK]->(t)
    )

    RETURN e.execution_id AS execution_id
    """

    result = neo4j_client.run_query(
        query,
        {
            "case_id": case_id,
            "task_id": task_id,
            "execution_id": execution_id,
            "created_at": created_at,
        },
    )

    if not result:
        raise ValueError(
            f"Could not create execution for {case_id}"
        )

    return execution_id


def start_agent_execution(
    execution_id: str,
    agent_id: str,
    task_id: str | None = None,
):
    agent_execution_id = (
        f"AEXEC-{uuid4().hex[:8].upper()}"
    )

    started_at = now_iso()

    query = """
    MATCH (e:Execution {
        execution_id: $execution_id
    })

    CREATE (a:AgentExecution {
        agent_execution_id: $agent_execution_id,
        agent_id: $agent_id,
        task_id: $task_id,
        status: 'RUNNING',
        started_at: $started_at
    })

    CREATE (e)-[:RUNS_AGENT]->(a)

    RETURN a.agent_execution_id AS agent_execution_id
    """

    result = neo4j_client.run_query(
        query,
        {
            "execution_id": execution_id,
            "agent_execution_id": agent_execution_id,
            "agent_id": agent_id,
            "task_id": task_id,
            "started_at": started_at,
        },
    )

    if not result:
        raise ValueError(
            f"Execution {execution_id} not found"
        )

    return agent_execution_id


def complete_agent_execution(
    agent_execution_id: str,
    result_summary: str | None = None,
):
    completed_at = now_iso()

    query = """
    MATCH (a:AgentExecution {
        agent_execution_id: $agent_execution_id
    })

    SET
        a.status = 'COMPLETED',
        a.completed_at = $completed_at,
        a.result_summary = $result_summary

    RETURN a
    """

    return neo4j_client.run_query(
        query,
        {
            "agent_execution_id": agent_execution_id,
            "completed_at": completed_at,
            "result_summary": result_summary,
        },
    )


def fail_agent_execution(
    agent_execution_id: str,
    error: str,
):
    completed_at = now_iso()

    query = """
    MATCH (a:AgentExecution {
        agent_execution_id: $agent_execution_id
    })

    SET
        a.status = 'FAILED',
        a.completed_at = $completed_at,
        a.error = $error

    RETURN a
    """

    return neo4j_client.run_query(
        query,
        {
            "agent_execution_id": agent_execution_id,
            "completed_at": completed_at,
            "error": error,
        },
    )


def complete_execution(
    execution_id: str,
    status: str = "COMPLETED",
):
    completed_at = now_iso()

    query = """
    MATCH (e:Execution {
        execution_id: $execution_id
    })

    SET
        e.status = $status,
        e.completed_at = $completed_at

    RETURN e
    """

    return neo4j_client.run_query(
        query,
        {
            "execution_id": execution_id,
            "status": status,
            "completed_at": completed_at,
        },
    )


def get_execution(execution_id: str):
    query = """
    MATCH (e:Execution {
        execution_id: $execution_id
    })

    OPTIONAL MATCH (e)-[:EXECUTES_TASK]->(t)
    OPTIONAL MATCH (e)-[:RUNS_AGENT]->(a)

    RETURN
        e {
            .*,
            task: t,
            agent_executions: collect(a)
        } AS execution
    """

    result = neo4j_client.run_query(
        query,
        {
            "execution_id": execution_id
        },
    )

    if not result:
        return None

    return result[0]["execution"]


def get_executions(case_id: str | None = None):
    if case_id:

        query = """
        MATCH (e:Execution {
            case_id: $case_id
        })

        OPTIONAL MATCH (e)-[:EXECUTES_TASK]->(t)
        OPTIONAL MATCH (e)-[:RUNS_AGENT]->(a)

        WITH e, t, collect(a) AS agent_executions

        RETURN
            e {
                .*,
                task: t,
                agent_executions: agent_executions
            } AS execution

        ORDER BY execution.created_at DESC
        """

        params = {
            "case_id": case_id
        }

    else:

        query = """
        MATCH (e:Execution)

        OPTIONAL MATCH (e)-[:EXECUTES_TASK]->(t)
        OPTIONAL MATCH (e)-[:RUNS_AGENT]->(a)

        WITH e, t, collect(a) AS agent_executions

        RETURN
            e {
                .*,
                task: t,
                agent_executions: agent_executions
            } AS execution

        ORDER BY execution.created_at DESC
        """

        params = {}

    result = neo4j_client.run_query(
        query,
        params,
    )

    return [
        row["execution"]
        for row in result
    ]