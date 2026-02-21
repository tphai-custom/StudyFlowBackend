from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.crud import slots as crud
from app.database import get_db
from app.models.user import User
from app.schemas.free_slot import FreeSlotCreate, FreeSlotSchema

router = APIRouter(prefix="/slots", tags=["free-slots"])


@router.get("/", response_model=list[FreeSlotSchema])
async def list_slots(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.list_slots(db, current_user.id)


@router.post("/", response_model=FreeSlotSchema, status_code=status.HTTP_201_CREATED)
async def create_slot(
    payload: FreeSlotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await crud.create_slot(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{slot_id}", response_model=FreeSlotSchema)
async def update_slot(
    slot_id: str,
    payload: FreeSlotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    slot = await crud.get_slot(db, slot_id)
    if not slot or slot.owner_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Slot not found")
    return await crud.update_slot(db, slot_id, payload)


@router.delete("/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(
    slot_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    slot = await crud.get_slot(db, slot_id)
    if not slot or slot.owner_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Slot not found")
    await crud.delete_slot(db, slot_id)
