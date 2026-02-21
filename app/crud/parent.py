"""CRUD helpers for parent–student linking and suggestions."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parent import ParentStudentLink, ParentSuggestion
from app.models.user import User


async def get_link(db: AsyncSession, parent_id: str, student_id: str) -> Optional[ParentStudentLink]:
    result = await db.execute(
        select(ParentStudentLink).where(
            ParentStudentLink.parent_id == parent_id,
            ParentStudentLink.student_id == student_id,
        )
    )
    return result.scalar_one_or_none()


async def create_link(db: AsyncSession, parent_id: str, student_id: str) -> ParentStudentLink:
    link = ParentStudentLink(
        id=str(uuid.uuid4()),
        parent_id=parent_id,
        student_id=student_id,
        status="pending",
    )
    db.add(link)
    await db.flush()
    return link


async def list_links_for_parent(
    db: AsyncSession, parent_id: str, status: Optional[str] = None
) -> list[ParentStudentLink]:
    stmt = select(ParentStudentLink).where(ParentStudentLink.parent_id == parent_id)
    if status:
        stmt = stmt.where(ParentStudentLink.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_links_for_student(
    db: AsyncSession, student_id: str
) -> list[ParentStudentLink]:
    result = await db.execute(
        select(ParentStudentLink).where(ParentStudentLink.student_id == student_id)
    )
    return list(result.scalars().all())


async def update_link_status(
    db: AsyncSession, link_id: str, status: str
) -> Optional[ParentStudentLink]:
    result = await db.execute(
        select(ParentStudentLink).where(ParentStudentLink.id == link_id)
    )
    link = result.scalar_one_or_none()
    if link:
        link.status = status
        await db.flush()
    return link


# ---- Suggestions ----

async def create_suggestion(
    db: AsyncSession,
    parent_id: str,
    student_id: str,
    type_: str,
    payload: dict,
    message: Optional[str] = None,
) -> ParentSuggestion:
    suggestion = ParentSuggestion(
        id=str(uuid.uuid4()),
        parent_id=parent_id,
        student_id=student_id,
        type=type_,
        payload=payload,
        message=message,
        status="pending",
    )
    db.add(suggestion)
    await db.flush()
    return suggestion


async def list_suggestions_for_student(
    db: AsyncSession, student_id: str, status: Optional[str] = None
) -> list[ParentSuggestion]:
    stmt = select(ParentSuggestion).where(ParentSuggestion.student_id == student_id)
    if status:
        stmt = stmt.where(ParentSuggestion.status == status)
    result = await db.execute(stmt.order_by(ParentSuggestion.created_at.desc()))
    return list(result.scalars().all())


async def list_suggestions_by_parent(
    db: AsyncSession, parent_id: str
) -> list[ParentSuggestion]:
    result = await db.execute(
        select(ParentSuggestion)
        .where(ParentSuggestion.parent_id == parent_id)
        .order_by(ParentSuggestion.created_at.desc())
    )
    return list(result.scalars().all())


async def update_suggestion_status(
    db: AsyncSession, suggestion_id: str, status: str, student_id: str
) -> Optional[ParentSuggestion]:
    result = await db.execute(
        select(ParentSuggestion).where(
            ParentSuggestion.id == suggestion_id,
            ParentSuggestion.student_id == student_id,
        )
    )
    suggestion = result.scalar_one_or_none()
    if suggestion:
        suggestion.status = status
        await db.flush()
    return suggestion
