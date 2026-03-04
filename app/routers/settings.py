from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.crud import settings as crud
from app.crud import parent as parent_crud
from app.database import get_db
from app.models.user import User
from app.schemas.settings import AppSettingsSchema

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettingsSchema)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await crud.get_settings(db)


@router.put("", response_model=AppSettingsSchema)
async def save_settings(
    payload: AppSettingsSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Enforce parent locks: reject changes to locked fields
    if current_user.role == "student":
        locked_fields = await parent_crud.get_locked_fields_for_student(db, current_user.id)
        if locked_fields:
            existing = await crud.get_settings(db)
            data = payload.model_dump(by_alias=False, exclude_unset=True)
            field_map = {
                "daily_limit_minutes": existing.daily_limit_minutes,
                "buffer_percent": existing.buffer_percent,
                "break_preset": existing.break_preset,
                "timezone": existing.timezone,
            }
            for f in locked_fields:
                if f in data and data[f] != field_map.get(f):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Trường '{f}' đã bị phụ huynh khoá 🔒. Không thể thay đổi.",
                    )
    return await crud.save_settings(db, payload)


@router.get("/effective")
async def get_effective_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    F: Effective settings — returns base settings PLUS parent override info.
    Includes:
      - effective_values: the actual values being used (after parent overrides)
      - locked_fields: which fields are locked
      - locked_values: the values the parent has set for locked fields
      - student_values: what the student originally had (may differ from effective if locked)
    """
    base = await crud.get_settings(db)
    student_values = {
        "daily_limit_minutes": base.daily_limit_minutes,
        "buffer_percent": base.buffer_percent,
        "break_preset": base.break_preset,
        "timezone": base.timezone,
    }

    locked_fields: list[str] = []
    locked_values: dict = {}

    if current_user.role == "student":
        locked_fields = await parent_crud.get_locked_fields_for_student(db, current_user.id)
        locked_values = await parent_crud.get_merged_locked_values_for_student(db, current_user.id) or {}

    # Build effective values: locked overrides student's preference
    effective = dict(student_values)
    for field in locked_fields:
        if field in locked_values and locked_values[field] is not None:
            effective[field] = locked_values[field]

    return {
        "effective_values": effective,
        "student_values": student_values,
        "locked_fields": locked_fields,
        "locked_values": {k: v for k, v in locked_values.items() if k in locked_fields},
    }
