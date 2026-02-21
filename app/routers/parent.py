"""Router: parent–student linking, child data view, and suggestions.

Requires role=parent for most endpoints. Students use a few endpoints
(incoming-links, respond to link requests, review suggestions).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.crud import parent as crud
from app.crud import tasks as tasks_crud
from app.crud import plan as plan_crud
from app.crud import habits as habits_crud
from app.crud import user as user_crud
from app.database import get_db
from app.models.user import User
from app.schemas.parent import (
    LinkRequest,
    LinkSchema,
    LinkStatusUpdate,
    SuggestionCreate,
    SuggestionSchema,
    SuggestionStatusUpdate,
)

router = APIRouter(prefix="/parent", tags=["parent"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _require_active_link(
    db: AsyncSession, parent_id: str, student_id: str
) -> None:
    """Raise 403 unless an active link exists between parent and student."""
    link = await crud.get_link(db, parent_id, student_id)
    if not link or link.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có liên kết hợp lệ với học sinh này.",
        )


# ---------------------------------------------------------------------------
# Link management (parent initiates)
# ---------------------------------------------------------------------------

@router.post("/link", response_model=LinkSchema, status_code=status.HTTP_201_CREATED)
async def request_link(
    payload: LinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Parent requests to link with a student using the student's link_code."""
    student = await user_crud.get_user_by_username(db, payload.child_username)
    if not student or student.role != "student":
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")
    if student.link_code != payload.link_code:
        raise HTTPException(status_code=400, detail="Mã liên kết không đúng")
    existing = await crud.get_link(db, current_user.id, student.id)
    if existing:
        raise HTTPException(status_code=409, detail="Đã gửi yêu cầu liên kết trước đó")
    link = await crud.create_link(db, current_user.id, student.id)
    await db.commit()
    return link


@router.get("/links", response_model=list[LinkSchema])
async def list_links(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """List all links (any status) initiated by this parent."""
    return await crud.list_links_for_parent(db, current_user.id)


@router.get("/children", response_model=list[LinkSchema])
async def list_children(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """List students with active links."""
    return await crud.list_links_for_parent(db, current_user.id, status="active")


# ---------------------------------------------------------------------------
# Student responds to incoming link requests
# ---------------------------------------------------------------------------

@router.get("/incoming-links", response_model=list[LinkSchema])
async def incoming_links(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Student sees who wants to link with them."""
    return await crud.list_links_for_student(db, current_user.id)


@router.patch("/links/{link_id}", response_model=LinkSchema)
async def respond_to_link(
    link_id: str,
    payload: LinkStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Student accepts or rejects a link request."""
    if payload.status not in ("active", "rejected"):
        raise HTTPException(status_code=400, detail="status phải là 'active' hoặc 'rejected'")
    link = await crud.update_link_status(db, link_id, payload.status)
    if not link or link.student_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu liên kết")
    await db.commit()
    return link


# ---------------------------------------------------------------------------
# Parent reads child data
# ---------------------------------------------------------------------------

@router.get("/child/{student_id}/tasks")
async def get_child_tasks(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, student_id)
    return await tasks_crud.list_tasks(db, student_id)


@router.get("/child/{student_id}/plan")
async def get_child_plan(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, student_id)
    plan = await plan_crud.get_latest_plan(db, student_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Chưa có kế hoạch")
    return plan


@router.get("/child/{student_id}/habits")
async def get_child_habits(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, student_id)
    return await habits_crud.list_habits(db, student_id)


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------

@router.post("/child/{student_id}/suggestions", response_model=SuggestionSchema, status_code=status.HTTP_201_CREATED)
async def create_suggestion(
    student_id: str,
    payload: SuggestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, student_id)
    suggestion = await crud.create_suggestion(
        db,
        parent_id=current_user.id,
        student_id=student_id,
        type_=payload.type,
        payload=payload.payload,
        message=payload.message,
    )
    await db.commit()
    return suggestion


@router.get("/child/{student_id}/suggestions", response_model=list[SuggestionSchema])
async def list_suggestions_for_child(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, student_id)
    return await crud.list_suggestions_by_parent(db, current_user.id)


@router.get("/my-suggestions", response_model=list[SuggestionSchema])
async def my_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Student sees suggestions sent to them (pending ones)."""
    return await crud.list_suggestions_for_student(db, current_user.id, status="pending")


@router.patch("/suggestions/{suggestion_id}", response_model=SuggestionSchema)
async def respond_to_suggestion(
    suggestion_id: str,
    payload: SuggestionStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    if payload.status not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="status phải là 'accepted' hoặc 'rejected'")
    suggestion = await crud.update_suggestion_status(
        db, suggestion_id, payload.status, current_user.id
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail="Không tìm thấy gợi ý")
    await db.commit()
    return suggestion
