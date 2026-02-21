from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import LibraryItem
from app.schemas.library import LibraryItemCreate


async def list_library(db: AsyncSession, owner_user_id: str) -> list[LibraryItem]:
    """Return system-shared items (owner_user_id IS NULL) + user's own items."""
    from sqlalchemy import or_, null
    result = await db.execute(
        select(LibraryItem)
        .where(or_(LibraryItem.owner_user_id == None, LibraryItem.owner_user_id == owner_user_id))  # noqa: E711
        .order_by(LibraryItem.subject, LibraryItem.title)
    )
    return list(result.scalars().all())


async def search_library(
    db: AsyncSession, owner_user_id: str, query: Optional[str] = None, subject: Optional[str] = None
) -> list[LibraryItem]:
    from sqlalchemy import or_
    stmt = select(LibraryItem).where(
        or_(LibraryItem.owner_user_id == None, LibraryItem.owner_user_id == owner_user_id)  # noqa: E711
    )
    items = (await db.execute(stmt)).scalars().all()
    results = []
    for item in items:
        match_query = (
            query.lower() in f"{item.title} {item.summary}".lower() if query else True
        )
        match_subject = item.subject == subject if subject else True
        if match_query and match_subject:
            results.append(item)
    return results


async def save_library_items(db: AsyncSession, items: list[LibraryItemCreate], owner_user_id: Optional[str] = None) -> list[LibraryItem]:
    saved = []
    for payload in items:
        data = payload.model_dump()
        item = LibraryItem(id=str(uuid.uuid4()), **data, owner_user_id=owner_user_id)
        db.add(item)
        saved.append(item)
    await db.flush()
    return saved
