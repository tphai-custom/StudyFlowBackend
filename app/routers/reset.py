from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db

router = APIRouter(prefix="/reset", tags=["reset"])


@router.delete("", status_code=204)
async def reset_all_data(db: AsyncSession = Depends(get_db)):
    """Delete all user data from every table."""
    tables = [
        "feedback",
        "library_items",
        "plan_records",
        "free_slots",
        "habits",
        "tasks",
        "settings",
        "profiles",
    ]
    for table in tables:
        await db.execute(text(f"DELETE FROM {table}"))
    await db.commit()
