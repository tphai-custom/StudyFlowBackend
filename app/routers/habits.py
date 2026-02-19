from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import habits as crud
from app.database import get_db
from app.schemas.habit import HabitCreate, HabitSchema

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("/", response_model=list[HabitSchema])
async def list_habits(db: AsyncSession = Depends(get_db)):
    return await crud.list_habits(db)


@router.post("/", response_model=HabitSchema, status_code=status.HTTP_201_CREATED)
async def create_habit(payload: HabitCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_habit(db, payload)


@router.put("/{habit_id}", response_model=HabitSchema)
async def update_habit(habit_id: str, payload: HabitCreate, db: AsyncSession = Depends(get_db)):
    habit = await crud.update_habit(db, habit_id, payload)
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    return habit


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(habit_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_habit(db, habit_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Habit not found")
