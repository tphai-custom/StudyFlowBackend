from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.crud import tasks as crud
from app.crud import plan as plan_crud
from app.database import get_db
from app.models.user import User
from app.schemas.task import TaskCreate, TaskSchema, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskSchema])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.list_tasks(db, current_user.id)


@router.post("/", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.create_task(db, payload, current_user.id)


@router.get("/{task_id}", response_model=TaskSchema)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await crud.get_task(db, task_id)
    if not task or task.owner_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskSchema)
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await crud.get_task(db, task_id)
    if not task or task.owner_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return await crud.update_task(db, task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await crud.get_task(db, task_id)
    if not task or task.owner_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    await crud.delete_task(db, task_id)
    await plan_crud.remove_task_from_plans(db, task_id, current_user.id)


@router.patch("/{task_id}/progress", response_model=TaskSchema)
async def update_progress(
    task_id: str,
    progress_minutes: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await crud.get_task(db, task_id)
    if not task or task.owner_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return await crud.update_task_progress(db, task_id, progress_minutes)
