from app.orchestrator.planner import plan_command
from app.orchestrator.task_store import task_store
from app.orchestrator.scheduler import scheduler


def submit_command(
    command: str,
    default_case_id: str | None = None,
):

    plan = plan_command(
        command,
        default_case_id,
    )

    created_tasks = []

    for planned_task in plan.tasks:

        case_id = (
            planned_task.case_id
            or default_case_id
        )

        if not case_id:
            raise ValueError(
                f"No case specified for task: "
                f"{planned_task.description}"
            )

        task = task_store.create_task(
            case_id=case_id,
            agent_id=planned_task.agent_id,
            description=planned_task.description,
            evidence_ids=planned_task.evidence_ids,
            priority=planned_task.priority,
            status=(
                "WAITING"
                if planned_task.depends_on_indexes
                else "READY"
            ),
        )

        created_tasks.append(task)

    # Add dependencies after all tasks exist.
    for index, planned_task in enumerate(plan.tasks):

        current_task = created_tasks[index]

        for dependency_index in (
            planned_task.depends_on_indexes
        ):

            if (
                dependency_index < 0
                or dependency_index >= len(created_tasks)
            ):
                raise ValueError(
                    "Invalid dependency index"
                )

            dependency_task = (
                created_tasks[dependency_index]
            )

            task_store.add_dependency(
                current_task["task_id"],
                dependency_task["task_id"],
            )

    # Wake scheduler in the background.
    scheduler.start()

    return {
        "command": command,
        "tasks": [
            task_store.get_task(
                task["task_id"]
            )
            for task in created_tasks
        ],
    }