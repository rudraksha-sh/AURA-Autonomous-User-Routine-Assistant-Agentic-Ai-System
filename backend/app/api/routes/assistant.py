from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.schemas.assistant import AssistantToolRequest, AssistantToolResponse
from app.services.assistant_tool_registry import execute_assistant_tool


router = APIRouter(prefix="/api/assistant", tags=["Assistant Tools"])


@router.post("/tools", response_model=AssistantToolResponse)
def run_assistant_tool(
    request: AssistantToolRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return execute_assistant_tool(db, user_id, request)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
