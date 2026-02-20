from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import tasks as crud
from app.crud import plan as plan_crud
from app.database import get_db
from app.schemas.task import TaskCreate, TaskSchema, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskSchema])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    rows = await crud.list_tasks(db)
    return rows


@router.post("/", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_task(db, payload)


@router.get("/{task_id}", response_model=TaskSchema)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskSchema)
async def update_task(task_id: str, payload: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await crud.update_task(db, task_id, payload)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    await plan_crud.remove_task_from_plans(db, task_id)


@router.patch("/{task_id}/progress", response_model=TaskSchema)
async def update_progress(task_id: str, progress_minutes: int, db: AsyncSession = Depends(get_db)):
    task = await crud.update_task_progress(db, task_id, progress_minutes)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
