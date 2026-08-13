from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.orchestrator.service import submit_command
from app.orchestrator.task_store import task_store
from app.orchestrator.scheduler import (
    scheduler,
    AGENT_CAPACITY,
)


router = APIRouter(
    prefix="/orchestrator",
    tags=["Orchestrator"],
)


class CommandRequest(BaseModel):
    command: str
    case_id: Optional[str] = None


@router.post("/command")
def orchestrator_command(
    request: CommandRequest,
):

    try:

        return submit_command(
            command=request.command,
            default_case_id=request.case_id,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.get("/tasks")
def get_tasks(
    case_id: Optional[str] = None,
):

    return {
        "tasks": task_store.get_tasks(
            case_id
        )
    }

@router.post("/tasks/{task_id}/retry")
def retry_task(task_id: str):

    try:
        task = task_store.get_task(task_id)

        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found",
            )

        if task["status"] not in (
            "FAILED",
            "HUMAN_REVIEW",
            "BLOCKED",
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Task {task_id} cannot be retried "
                    f"from status {task['status']}"
                ),
            )

        updated_task = task_store.retry_task(task_id)

        if not updated_task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found",
            )

        return {
            "message": "Task queued for retry",
            "task": updated_task,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

@router.get("/status")
def get_orchestrator_status():

    tasks = task_store.get_tasks()

    agents = []

    for agent_id, capacity in (
        AGENT_CAPACITY.items()
    ):

        running = task_store.get_running_count(
            agent_id
        )

        agents.append(
            {
                "agent_id": agent_id,
                "capacity": capacity,
                "running": running,
                "available": max(
                    capacity - running,
                    0,
                ),
            }
        )

    return {
        "agents": agents,
        "tasks": {
            "ready": sum(
                t["status"] == "READY"
                for t in tasks
            ),
            "waiting": sum(
                t["status"] == "WAITING"
                for t in tasks
            ),
            "running": sum(
                t["status"] == "RUNNING"
                for t in tasks
            ),
            "completed": sum(
                t["status"] == "COMPLETED"
                for t in tasks
            ),
            "failed": sum(
                t["status"] == "FAILED"
                for t in tasks
            ),
            "human_review": sum(
                t["status"] == "HUMAN_REVIEW"
                for t in tasks
            ),
        },
    }


@router.post("/start")
def start_scheduler():

    scheduler.start()

    return {
        "status": "scheduler_started"
    }