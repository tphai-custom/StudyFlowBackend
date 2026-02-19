from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import LibraryItem
from app.schemas.library import LibraryItemCreate


async def list_library(db: AsyncSession) -> list[LibraryItem]:
    result = await db.execute(select(LibraryItem).order_by(LibraryItem.subject, LibraryItem.title))
    return list(result.scalars().all())


async def search_library(
    db: AsyncSession, query: Optional[str] = None, subject: Optional[str] = None
) -> list[LibraryItem]:
    stmt = select(LibraryItem)
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


async def save_library_items(db: AsyncSession, items: list[LibraryItemCreate]) -> list[LibraryItem]:
    saved = []
    for payload in items:
        data = payload.model_dump()
        item = LibraryItem(id=str(uuid.uuid4()), **data)
        db.add(item)
        saved.append(item)
    await db.flush()
    return saved
