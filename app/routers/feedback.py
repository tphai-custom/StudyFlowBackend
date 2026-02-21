from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.crud import feedback as crud
from app.database import get_db
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackSchema

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("/", response_model=list[FeedbackSchema])
async def list_feedback(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.list_feedback(db, current_user.id)


@router.post("/", response_model=FeedbackSchema)
async def submit_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.save_feedback(db, payload, current_user.id)
