"""Reports router — shared day/week reports for student and parent.

F: Student and parent both call these endpoints.
   Student:  GET /reports/day (uses own data)
   Parent:   GET /reports/day?student_id=<id> (requires active link)

AC4: BREAK excluded from completion %; shown separately.
E1: Separate day vs week endpoints with correct title/shape.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_current_user
from app.crud import parent as parent_crud
from app.database import get_db
from app.models.plan import PlanRecord
from app.models.user import User
from app.planner.report_service import _build_report_day, _build_report_week, _parse_week

router = APIRouter(prefix="/reports", tags=["reports"])

_TZ_VN = timezone(timedelta(hours=7))


async def _get_sessions(db: AsyncSession, student_id: str) -> list[dict]:
    """Fetch latest plan sessions for the given student."""
    result = await db.execute(
        select(PlanRecord)
        .where(PlanRecord.owner_user_id == student_id)
        .order_by(PlanRecord.created_at.desc())
        .limit(1)
    )
    plan = result.scalar_one_or_none()
    return plan.sessions if plan else []


async def _resolve_student(
    db: AsyncSession,
    current_user: User,
    student_id: str | None,
) -> str:
    """Resolve which student's data to query. Auth-checks parent role."""
    if not student_id or student_id == current_user.id:
        return current_user.id
    # student_id differs from current user → requires parent role
    if current_user.role != "parent":
        raise HTTPException(status_code=403, detail="Chỉ phụ huynh mới xem được dữ liệu học sinh khác")
    link = await parent_crud.get_link(db, current_user.id, student_id)
    if not link or link.status != "active":
        raise HTTPException(status_code=403, detail="Không có liên kết hợp lệ với học sinh này")
    return student_id


@router.get("/day")
async def get_report_day(
    date: str = Query(
        default=None,
        description="YYYY-MM-DD (VN timezone). Defaults to today.",
    ),
    student_id: str = Query(default=None, description="Target student (parent/admin use)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    E2: Day report — STUDY + HABIT minutes done/planned + BREAK shown separately.
    AC4: BREAK is not counted in completion_rate.
    """
    target_id = await _resolve_student(db, current_user, student_id)
    # Default to today in VN timezone
    if not date:
        date = datetime.now(_TZ_VN).strftime("%Y-%m-%d")
    sessions = await _get_sessions(db, target_id)
    return _build_report_day(sessions, date)


@router.get("/week")
async def get_report_week(
    week: str = Query(
        default=None,
        description="ISO week string YYYY-Www (e.g. 2026-W10). Defaults to current week.",
    ),
    student_id: str = Query(default=None, description="Target student (parent/admin use)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    E1: Week report — aggregates day-level reports for the 7-day ISO week.
    AC4: BREAK excluded from completion_rate.
    """
    target_id = await _resolve_student(db, current_user, student_id)
    if not week:
        today = datetime.now(_TZ_VN)
        week = today.strftime("%Y-W%W")
    start_date, end_date = _parse_week(week)
    sessions = await _get_sessions(db, target_id)
    return _build_report_week(sessions, start_date, end_date, week)
