from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_draft import ImportDraft
from app.schemas.import_draft import ImportDraftCreate, ImportDraftUpdate


async def list_drafts(db: AsyncSession, owner_user_id: str, draft_type: Optional[str] = None) -> list[ImportDraft]:
    query = select(ImportDraft).where(ImportDraft.owner_user_id == owner_user_id).order_by(ImportDraft.created_at.desc())
    if draft_type:
        query = query.where(ImportDraft.draft_type == draft_type)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_draft(db: AsyncSession, draft_id: str) -> Optional[ImportDraft]:
    result = await db.execute(select(ImportDraft).where(ImportDraft.id == draft_id))
    return result.scalar_one_or_none()


async def create_draft(db: AsyncSession, payload: ImportDraftCreate, owner_user_id: str) -> ImportDraft:
    items_json = [item.model_dump() for item in payload.items]
    draft = ImportDraft(
        id=str(uuid.uuid4()),
        draft_type=payload.draftType,
        source_id=payload.sourceId,
        name=payload.name,
        description=payload.description,
        items=items_json,
        owner_user_id=owner_user_id,
        status="draft",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(draft)
    await db.flush()
    return draft


async def update_draft(db: AsyncSession, draft_id: str, payload: ImportDraftUpdate) -> Optional[ImportDraft]:
    draft = await get_draft(db, draft_id)
    if draft is None:
        return None
    if payload.name is not None:
        draft.name = payload.name
    if payload.description is not None:
        draft.description = payload.description
    if payload.items is not None:
        draft.items = [item.model_dump() for item in payload.items]
    draft.updated_at = datetime.utcnow()
    await db.flush()
    return draft


async def finalize_draft(db: AsyncSession, draft_id: str) -> Optional[ImportDraft]:
    draft = await get_draft(db, draft_id)
    if draft is None:
        return None
    draft.status = "finalized"
    draft.updated_at = datetime.utcnow()
    await db.flush()
    return draft


async def delete_draft(db: AsyncSession, draft_id: str) -> bool:
    result = await db.execute(delete(ImportDraft).where(ImportDraft.id == draft_id))
    return result.rowcount > 0
