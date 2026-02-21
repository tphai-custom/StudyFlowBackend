from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/reset", tags=["reset"])


@router.delete("", status_code=204)
async def reset_all_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all user data belonging to the authenticated user."""
    owner_id = current_user.id
    tables_with_owner = [
        "feedback",
        "plan_records",
        "free_slots",
        "habits",
        "tasks",
        "import_drafts",
    ]
    for table in tables_with_owner:
        await db.execute(
            text(f"DELETE FROM {table} WHERE owner_user_id = :uid"),
            {"uid": owner_id},
        )
    # settings and profiles are per-user too but single-row; leave them intact.
    await db.commit()
