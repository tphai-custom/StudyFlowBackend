from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.crud import library as crud
from app.database import get_db
from app.models.library import ALLOWED_SUBJECTS, ALLOWED_TYPES, SUBJECT_LABELS
from app.models.user import User
from app.schemas.library import LibraryItemCreate, LibraryItemSchema, LibraryItemV2Schema

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/subjects")
async def get_subjects():
    """Return the 5 allowed subjects with labels."""
    return [{"value": k, "label": v} for k, v in SUBJECT_LABELS.items()]


@router.get("/grades")
async def get_grades():
    """Return allowed grade range 6-10."""
    return list(range(6, 11))


@router.get("/types")
async def get_resource_types():
    """Return allowed resource types."""
    return ALLOWED_TYPES


# ---------------------------------------------------------------------------
# v2 endpoint – one record per (grade, subject) with 4 content groups
# ---------------------------------------------------------------------------

@router.get("/v2", response_model=list[LibraryItemV2Schema])
async def list_library_v2(
    grade: Optional[int] = Query(default=None, ge=6, le=10),
    subject: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get library items in v2 format (lessons/summaries/exercises/videos).

    Filters: grade (6-10), subject (toan|ngu_van|tieng_anh|lich_su|dia_li), q (keyword).
    Sort: grade asc, subject asc.
    """
    return await crud.list_library_v2(db, grade=grade, subject=subject, q=q, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# Legacy v1 endpoints (kept for backward compatibility)
# ---------------------------------------------------------------------------

@router.get("", response_model=list[LibraryItemSchema])
async def list_library(
    q: Optional[str] = Query(default=None),
    subject: Optional[str] = Query(default=None),
    grade: Optional[int] = Query(default=None, ge=6, le=10),
    resource_type: Optional[str] = Query(default=None, alias="type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if any([q, subject, grade, resource_type]):
        return await crud.search_library(
            db, current_user.id, query=q, subject=subject, grade=grade, resource_type=resource_type
        )
    return await crud.list_library(db, current_user.id)


@router.post("", response_model=list[LibraryItemSchema])
async def save_library_items(
    items: list[LibraryItemCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await crud.save_library_items(db, items, current_user.id)
    await db.commit()
    return result


@router.post("/seed", response_model=dict)
async def seed_library(
    reseed: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seed system library data. reseed=true will delete & re-seed."""
    if reseed:
        count = await crud.reseed_library(db)
    else:
        count = await crud.seed_library(db)
    await db.commit()
    return {"seeded": count, "message": f"Seeded {count} items" if count else "Already seeded – use ?reseed=true to force"}

