import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FeedbackModel

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    label: str
    note: Optional[str] = None
    planVersion: int = 0


def feedback_to_dict(f: FeedbackModel) -> dict:
    return {
        "id": f.id,
        "label": f.label,
        "note": f.note,
        "submittedAt": f.submittedAt,
        "planVersion": f.planVersion,
    }


@router.get("/")
def list_feedback(db: Session = Depends(get_db)):
    return [feedback_to_dict(f) for f in db.query(FeedbackModel).all()]


@router.post("/", status_code=201)
def create_feedback(body: FeedbackCreate, db: Session = Depends(get_db)):
    now = datetime.utcnow().isoformat() + "Z"
    fb = FeedbackModel(
        id=str(uuid.uuid4()),
        label=body.label,
        note=body.note,
        submittedAt=now,
        planVersion=body.planVersion,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return feedback_to_dict(fb)
