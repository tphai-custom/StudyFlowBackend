import uuid
from datetime import datetime
from typing import List, Optional, Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TaskModel

router = APIRouter(prefix="/tasks", tags=["tasks"])


class MilestoneSchema(BaseModel):
    id: str
    title: str
    minutesEstimate: int


class TaskCreate(BaseModel):
    subject: str
    title: str
    deadline: str
    timezone: str = "Asia/Ho_Chi_Minh"
    difficulty: int = 3
    durationEstimateMin: int = 30
    durationEstimateMax: int = 60
    durationUnit: str = "minutes"
    estimatedMinutes: int = 60
    importance: Optional[int] = None
    contentFocus: Optional[str] = None
    successCriteria: List[str] = []
    milestones: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None


class TaskUpdate(BaseModel):
    subject: Optional[str] = None
    title: Optional[str] = None
    deadline: Optional[str] = None
    timezone: Optional[str] = None
    difficulty: Optional[int] = None
    durationEstimateMin: Optional[int] = None
    durationEstimateMax: Optional[int] = None
    durationUnit: Optional[str] = None
    estimatedMinutes: Optional[int] = None
    importance: Optional[int] = None
    contentFocus: Optional[str] = None
    successCriteria: Optional[List[str]] = None
    milestones: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    progressMinutes: Optional[int] = None


def task_to_dict(t: TaskModel) -> dict:
    return {
        "id": t.id,
        "subject": t.subject,
        "title": t.title,
        "deadline": t.deadline,
        "timezone": t.timezone,
        "difficulty": t.difficulty,
        "durationEstimateMin": t.durationEstimateMin,
        "durationEstimateMax": t.durationEstimateMax,
        "durationUnit": t.durationUnit,
        "estimatedMinutes": t.estimatedMinutes,
        "importance": t.importance,
        "contentFocus": t.contentFocus,
        "successCriteria": t.successCriteria or [],
        "milestones": t.milestones,
        "notes": t.notes,
        "createdAt": t.createdAt,
        "updatedAt": t.updatedAt,
        "progressMinutes": t.progressMinutes,
    }


@router.get("/")
def list_tasks(db: Session = Depends(get_db)):
    return [task_to_dict(t) for t in db.query(TaskModel).all()]


@router.post("/", status_code=201)
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    now = datetime.utcnow().isoformat() + "Z"
    task = TaskModel(
        id=str(uuid.uuid4()),
        subject=body.subject,
        title=body.title,
        deadline=body.deadline,
        timezone=body.timezone,
        difficulty=body.difficulty,
        durationEstimateMin=body.durationEstimateMin,
        durationEstimateMax=body.durationEstimateMax,
        durationUnit=body.durationUnit,
        estimatedMinutes=body.estimatedMinutes,
        importance=body.importance,
        contentFocus=body.contentFocus,
        successCriteria=body.successCriteria,
        milestones=body.milestones,
        notes=body.notes,
        createdAt=now,
        updatedAt=now,
        progressMinutes=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task_to_dict(task)


@router.put("/{task_id}")
def update_task(task_id: str, body: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    task.updatedAt = datetime.utcnow().isoformat() + "Z"
    db.commit()
    db.refresh(task)
    return task_to_dict(task)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
