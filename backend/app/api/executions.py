from typing import Optional

from fastapi import APIRouter, HTTPException

from app.services.execution_service import (
    get_execution,
    get_executions,
)


router = APIRouter(
    prefix="/executions",
    tags=["Executions"],
)


@router.get("")
def list_executions(
    case_id: Optional[str] = None,
):

    return {
        "executions": get_executions(
            case_id
        )
    }


@router.get("/{execution_id}")
def execution_detail(
    execution_id: str,
):

    execution = get_execution(
        execution_id
    )

    if not execution:

        raise HTTPException(
            status_code=404,
            detail="Execution not found",
        )

    return execution