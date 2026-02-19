from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TaskModel, SlotModel, HabitModel, LibraryItemModel, PlanModel, SessionModel

router = APIRouter(prefix="/reset", tags=["reset"])


@router.delete("", status_code=204)
def reset_all(db: Session = Depends(get_db)):
    db.query(SessionModel).delete()
    db.query(PlanModel).delete()
    db.query(LibraryItemModel).delete()
    db.query(HabitModel).delete()
    db.query(SlotModel).delete()
    db.query(TaskModel).delete()
    db.commit()
