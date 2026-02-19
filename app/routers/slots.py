import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SlotModel

router = APIRouter(prefix="/slots", tags=["slots"])


class SlotCreate(BaseModel):
    weekday: int
    startTime: str
    endTime: str
    capacityMinutes: int = 0
    source: Optional[str] = "user"


class SlotUpdate(BaseModel):
    weekday: Optional[int] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    capacityMinutes: Optional[int] = None
    source: Optional[str] = None


def slot_to_dict(s: SlotModel) -> dict:
    return {
        "id": s.id,
        "weekday": s.weekday,
        "startTime": s.startTime,
        "endTime": s.endTime,
        "capacityMinutes": s.capacityMinutes,
        "source": s.source,
        "createdAt": s.createdAt,
    }


@router.get("/")
def list_slots(db: Session = Depends(get_db)):
    return [slot_to_dict(s) for s in db.query(SlotModel).all()]


@router.post("/", status_code=201)
def create_slot(body: SlotCreate, db: Session = Depends(get_db)):
    now = datetime.utcnow().isoformat() + "Z"
    slot = SlotModel(
        id=str(uuid.uuid4()),
        weekday=body.weekday,
        startTime=body.startTime,
        endTime=body.endTime,
        capacityMinutes=body.capacityMinutes,
        source=body.source,
        createdAt=now,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot_to_dict(slot)


@router.put("/{slot_id}")
def update_slot(slot_id: str, body: SlotUpdate, db: Session = Depends(get_db)):
    slot = db.query(SlotModel).filter(SlotModel.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(slot, field, value)
    db.commit()
    db.refresh(slot)
    return slot_to_dict(slot)


@router.delete("/{slot_id}", status_code=204)
def delete_slot(slot_id: str, db: Session = Depends(get_db)):
    slot = db.query(SlotModel).filter(SlotModel.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    db.delete(slot)
    db.commit()
