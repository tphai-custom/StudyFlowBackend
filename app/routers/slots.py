from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import slots as crud
from app.database import get_db
from app.schemas.free_slot import FreeSlotCreate, FreeSlotSchema

router = APIRouter(prefix="/slots", tags=["free-slots"])


@router.get("/", response_model=list[FreeSlotSchema])
async def list_slots(db: AsyncSession = Depends(get_db)):
    return await crud.list_slots(db)


@router.post("/", response_model=FreeSlotSchema, status_code=status.HTTP_201_CREATED)
async def create_slot(payload: FreeSlotCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await crud.create_slot(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{slot_id}", response_model=FreeSlotSchema)
async def update_slot(slot_id: str, payload: FreeSlotCreate, db: AsyncSession = Depends(get_db)):
    slot = await crud.update_slot(db, slot_id, payload)
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")
    return slot


@router.delete("/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(slot_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_slot(db, slot_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Slot not found")
