from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.agents.memory.agent import active_memories, save_memory
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.memory import PlanningMemory
from app.models.user import User

router = APIRouter(prefix="/api/v1/memory", tags=["Planning memory"])


class MemoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=500)
    use_for_planning: StrictBool = False
    retention_days: int = Field(default=30, ge=1, le=90)


class MemoryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    text: str
    use_for_planning: bool
    expires_at: datetime


@router.get("", response_model=list[MemoryView])
def memories(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return list(db.scalars(active_memories(user_id).order_by(PlanningMemory.id).limit(20)))


def _save(db, user_id, memory_id, body):
    try:
        return save_memory(db, user_id, memory_id, body.text, body.use_for_planning, body.retention_days)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.post("", response_model=MemoryView, status_code=201)
def create(body: MemoryInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return _save(db, user_id, str(uuid4()), body)


@router.put("/{memory_id}", response_model=MemoryView)
def update(memory_id: UUID, body: MemoryInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    db.scalar(select(User.id).where(User.id == user_id).with_for_update(key_share=True))
    if db.scalar(active_memories(user_id).where(PlanningMemory.id == str(memory_id))) is None:
        raise HTTPException(404, "Memory not found.")
    return _save(db, user_id, str(memory_id), body)


@router.delete("/{memory_id}", status_code=204)
def remove(memory_id: UUID, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    db.scalar(select(User.id).where(User.id == user_id).with_for_update(key_share=True))
    result = db.execute(delete(PlanningMemory).where(
        PlanningMemory.id == str(memory_id), PlanningMemory.user_id == user_id,
    ))
    if not result.rowcount:
        raise HTTPException(404, "Memory not found.")
    db.commit()


@router.delete("", status_code=204)
def reset(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    db.scalar(select(User.id).where(User.id == user_id).with_for_update(key_share=True))
    db.execute(delete(PlanningMemory).where(PlanningMemory.user_id == user_id))
    db.commit()
