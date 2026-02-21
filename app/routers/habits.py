from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.crud import habits as crud
from app.crud import plan as plan_crud
from app.database import get_db
from app.models.user import User
from app.schemas.habit import HabitCreate, HabitSchema

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("/", response_model=list[HabitSchema])
async def list_habits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.list_habits(db, current_user.id)


@router.post("/", response_model=HabitSchema, status_code=status.HTTP_201_CREATED)
async def create_habit(
    payload: HabitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.create_habit(db, payload, current_user.id)


@router.put("/{habit_id}", response_model=HabitSchema)
async def update_habit(
    habit_id: str,
    payload: HabitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    habit = await crud.get_habit(db, habit_id)
    if not habit or habit.owner_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Habit not found")
    return await crud.update_habit(db, habit_id, payload)


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(
    habit_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    habit = await crud.get_habit(db, habit_id)
    if not habit or habit.owner_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Habit not found")
    await crud.delete_habit(db, habit_id)
    await plan_crud.remove_habit_from_plans(db, habit_id, current_user.id)
