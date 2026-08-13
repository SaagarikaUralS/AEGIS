from datetime import datetime, timezone
from uuid import uuid4

from app.knowledge_graph.neo4j_client import neo4j_client


class TaskStore:

    def create_task(
        self,
        case_id: str,
        agent_id: str,
        description: str,
        evidence_ids: list[str] | None = None,
        priority: int = 5,
        max_retries: int = 2,
        status: str = "READY",
    ):
        task_id = f"TASK-{uuid4().hex[:8].upper()}"
        created_at = datetime.now(timezone.utc).isoformat()

        query = """
        MATCH (c:Case {case_id: $case_id})

        CREATE (t:InvestigationTask {
            task_id: $task_id,
            case_id: $case_id,
            agent_id: $agent_id,
            description: $description,
            evidence_ids: $evidence_ids,
            status: $status,
            priority: $priority,
            attempts: 0,
            max_retries: $max_retries,
            created_at: $created_at
        })

        CREATE (c)-[:HAS_TASK]->(t)

        RETURN t
        """

        result = neo4j_client.run_query(
            query,
            {
                "case_id": case_id,
                "task_id": task_id,
                "agent_id": agent_id,
                "description": description,
                "evidence_ids": evidence_ids or [],
                "status": status,
                "priority": priority,
                "max_retries": max_retries,
                "created_at": created_at,
            },
        )

        if not result:
            raise ValueError(f"Case {case_id} does not exist")

        return self.get_task(task_id)

    def add_dependency(self, task_id: str, dependency_task_id: str):
        query = """
        MATCH (t:InvestigationTask {task_id: $task_id})
        MATCH (d:InvestigationTask {task_id: $dependency_task_id})

        CREATE (t)-[:DEPENDS_ON]->(d)

        SET t.status = 'WAITING'

        RETURN t.task_id AS task_id
        """

        return neo4j_client.run_query(
            query,
            {
                "task_id": task_id,
                "dependency_task_id": dependency_task_id,
            },
        )

    def get_task(self, task_id: str):
        query = """
        MATCH (t:InvestigationTask {task_id: $task_id})

        OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d:InvestigationTask)

        WITH t, collect(d.task_id) AS dependency_ids

        RETURN {
            task_id: t.task_id,
            case_id: t.case_id,
            agent_id: t.agent_id,
            description: t.description,
            evidence_ids: t.evidence_ids,
            status: t.status,
            priority: t.priority,
            attempts: t.attempts,
            max_retries: t.max_retries,
            created_at: t.created_at,
            started_at: t.started_at,
            completed_at: t.completed_at,
            error: t.error,
            depends_on: dependency_ids
        } AS task
        """

        result = neo4j_client.run_query(
            query,
            {"task_id": task_id},
        )

        if not result:
            return None

        return result[0]["task"]

    def get_tasks(self, case_id: str | None = None):

        if case_id:

            query = """
            MATCH (t:InvestigationTask {case_id: $case_id})

            OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d:InvestigationTask)

            WITH
                t,
                collect(d.task_id) AS dependency_ids

            RETURN
                t {
                    .*,
                    depends_on: dependency_ids
                } AS task

            ORDER BY
                task.priority ASC,
                task.created_at ASC
            """

            params = {
                "case_id": case_id
            }

        else:

            query = """
            MATCH (t:InvestigationTask)

            OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d:InvestigationTask)

            WITH
                t,
                collect(d.task_id) AS dependency_ids

            RETURN
                t {
                    .*,
                    depends_on: dependency_ids
                } AS task

            ORDER BY
                task.priority ASC,
                task.created_at ASC
            """

            params = {}

        result = neo4j_client.run_query(
            query,
            params,
        )

        return [
            row["task"]
            for row in result
        ]
    def get_ready_tasks(self):
        query = """
        MATCH (t:InvestigationTask)
        WHERE t.status = 'READY'

        RETURN t {
            .*
        } AS task

        ORDER BY
            t.priority ASC,
            t.created_at ASC
        """

        result = neo4j_client.run_query(query)

        return [row["task"] for row in result]

    def get_running_count(self, agent_id: str):
        query = """
        MATCH (t:InvestigationTask)
        WHERE t.agent_id = $agent_id
        AND t.status = 'RUNNING'

        RETURN count(t) AS count
        """

        result = neo4j_client.run_query(
            query,
            {"agent_id": agent_id},
        )

        return result[0]["count"]

    def mark_running(self, task_id: str):
        now = datetime.now(timezone.utc).isoformat()

        query = """
        MATCH (t:InvestigationTask {task_id: $task_id})

        SET
            t.status = 'RUNNING',
            t.started_at = $now,
            t.attempts = t.attempts + 1

        RETURN t
        """

        return neo4j_client.run_query(
            query,
            {
                "task_id": task_id,
                "now": now,
            },
        )

    def mark_completed(self, task_id: str):
        now = datetime.now(timezone.utc).isoformat()

        query = """
        MATCH (t:InvestigationTask {task_id: $task_id})

        SET
            t.status = 'COMPLETED',
            t.completed_at = $now,
            t.error = null

        RETURN t
        """

        return neo4j_client.run_query(
            query,
            {
                "task_id": task_id,
                "now": now,
            },
        )

    def mark_failed(self, task_id: str, error: str):
        query = """
        MATCH (t:InvestigationTask {task_id: $task_id})

        SET
            t.status = 'FAILED',
            t.error = $error

        RETURN t
        """

        return neo4j_client.run_query(
            query,
            {
                "task_id": task_id,
                "error": error,
            },
        )

    def mark_ready_for_retry(self, task_id: str, error: str):
        query = """
        MATCH (t:InvestigationTask {task_id: $task_id})

        SET
            t.status = 'READY',
            t.error = $error

        RETURN t
        """

        return neo4j_client.run_query(
            query,
            {
                "task_id": task_id,
                "error": error,
            },
        )

    def retry_task(self, task_id: str):
        query = """
        MATCH (t:InvestigationTask {task_id: $task_id})

        SET
            t.status = 'READY',
            t.error = null,
            t.started_at = null,
            t.completed_at = null

        RETURN t
        """

        result = neo4j_client.run_query(
            query,
            {
                "task_id": task_id,
            },
        )

        if not result:
            return None

        return self.get_task(task_id)

    def mark_human_review(self, task_id: str, error: str):
        query = """
        MATCH (t:InvestigationTask {task_id: $task_id})

        SET
            t.status = 'HUMAN_REVIEW',
            t.error = $error

        RETURN t
        """

        return neo4j_client.run_query(
            query,
            {
                "task_id": task_id,
                "error": error,
            },
        )

    def mark_blocked(self, task_id: str, reason: str):
        query = """
        MATCH (t:InvestigationTask {task_id: $task_id})

        SET
            t.status = 'BLOCKED',
            t.error = $reason

        RETURN t
        """

        return neo4j_client.run_query(
            query,
            {
                "task_id": task_id,
                "reason": reason,
            },
        )

    def refresh_waiting_tasks(self):
        """
        Move WAITING tasks to READY when all dependencies completed.

        Block tasks if any dependency reached HUMAN_REVIEW.
        """

        query = """
        MATCH (t:InvestigationTask)
        WHERE t.status = 'WAITING'

        OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d:InvestigationTask)

        WITH t, collect(d.status) AS dependency_statuses

        FOREACH (_ IN CASE
            WHEN size(dependency_statuses) > 0
                 AND ALL(x IN dependency_statuses WHERE x = 'COMPLETED')
            THEN [1]
            ELSE []
        END |
            SET t.status = 'READY',
                t.error = null
        )

        FOREACH (_ IN CASE
            WHEN ANY(x IN dependency_statuses
                     WHERE x IN ['FAILED', 'HUMAN_REVIEW', 'BLOCKED'])
            THEN [1]
            ELSE []
        END |
            SET t.status = 'BLOCKED',
                t.error = 'Dependency failed or requires human review'
        )

        RETURN count(t) AS updated
        """

        return neo4j_client.run_query(query)


task_store = TaskStore()