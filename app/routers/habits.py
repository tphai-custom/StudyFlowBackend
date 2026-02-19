import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import HabitModel

router = APIRouter(prefix="/habits", tags=["habits"])


class HabitCreate(BaseModel):
    name: str
    cadence: str = "daily"
    weekday: Optional[int] = None
    minutes: int = 30
    preset: Optional[str] = None
    preferredStart: Optional[str] = None
    energyWindow: Optional[str] = None


class HabitUpdate(BaseModel):
    name: Optional[str] = None
    cadence: Optional[str] = None
    weekday: Optional[int] = None
    minutes: Optional[int] = None
    preset: Optional[str] = None
    preferredStart: Optional[str] = None
    energyWindow: Optional[str] = None


def habit_to_dict(h: HabitModel) -> dict:
    return {
        "id": h.id,
        "name": h.name,
        "cadence": h.cadence,
        "weekday": h.weekday,
        "minutes": h.minutes,
        "preset": h.preset,
        "preferredStart": h.preferredStart,
        "energyWindow": h.energyWindow,
        "createdAt": h.createdAt,
    }


@router.get("/")
def list_habits(db: Session = Depends(get_db)):
    return [habit_to_dict(h) for h in db.query(HabitModel).all()]


@router.post("/", status_code=201)
def create_habit(body: HabitCreate, db: Session = Depends(get_db)):
    now = datetime.utcnow().isoformat() + "Z"
    habit = HabitModel(
        id=str(uuid.uuid4()),
        name=body.name,
        cadence=body.cadence,
        weekday=body.weekday,
        minutes=body.minutes,
        preset=body.preset,
        preferredStart=body.preferredStart,
        energyWindow=body.energyWindow,
        createdAt=now,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit_to_dict(habit)


@router.put("/{habit_id}")
def update_habit(habit_id: str, body: HabitUpdate, db: Session = Depends(get_db)):
    habit = db.query(HabitModel).filter(HabitModel.id == habit_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(habit, field, value)
    db.commit()
    db.refresh(habit)
    return habit_to_dict(habit)


@router.delete("/{habit_id}", status_code=204)
def delete_habit(habit_id: str, db: Session = Depends(get_db)):
    habit = db.query(HabitModel).filter(HabitModel.id == habit_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    db.delete(habit)
    db.commit()
