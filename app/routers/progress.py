"""Router: unified progress endpoints (1 formula, 1 source, used by student + parent).

E: "1 công thức – 1 nguồn dữ liệu – 1 API dùng chung"

Formula:
  Task progress:
    planned_study_minutes = SUM(session.minutes WHERE task_id=X AND source='task')
    done_study_minutes    = SUM(session.minutes WHERE task_id=X AND source='task' AND done=True)
    progress              = done_study_minutes / planned_study_minutes

  Week/Day progress (Option A: study + habit, exclude break):
    total_planned = SUM(session.minutes WHERE source != 'break')
    total_done    = SUM(session.minutes WHERE source != 'break' AND status='done')
    completion    = total_done / total_planned
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_current_user, require_role
from app.crud import plan as plan_crud
from app.crud import tasks as tasks_crud
from app.crud import parent as parent_crud
from app.database import get_db
from app.models.plan import PlanRecord
from app.models.user import User

router = APIRouter(prefix="/progress", tags=["progress"])

_TZ_VN = timezone(timedelta(hours=7))


def _get_day_range_vn(range_str: str) -> tuple[str, str]:
    """Return (start_iso_date, end_iso_date) in VN timezone for 'day' or 'week'."""
    now_vn = datetime.now(_TZ_VN)
    if range_str == "day":
        today = now_vn.strftime("%Y-%m-%d")
        return today, today
    else:  # week — Mon to Sun
        dow = now_vn.weekday()  # 0=Mon
        mon = now_vn - timedelta(days=dow)
        sun = mon + timedelta(days=6)
        return mon.strftime("%Y-%m-%d"), sun.strftime("%Y-%m-%d")


def _compute_task_progress(sessions: list[dict], task_id: str) -> dict:
    """Compute progress for a specific task from plan sessions (study only)."""
    planned = 0
    done = 0
    done_sessions = 0
    total_sessions = 0

    for s in sessions:
        # Only count study-type sessions (source='task' or 'study', not break/habit)
        src = s.get("source", "task")
        if src == "break":
            continue
        tid = s.get("taskId") or s.get("task_id")
        if tid != task_id:
            continue
        mins = s.get("minutes", 0)
        planned += mins
        total_sessions += 1
        if s.get("status") == "done":
            done += mins
            done_sessions += 1

    if planned == 0:
        return {
            "task_id": task_id,
            "planned_study_minutes": 0,
            "done_study_minutes": 0,
            "progress_percent": 0,
            "done_sessions": 0,
            "total_sessions": 0,
        }

    return {
        "task_id": task_id,
        "planned_study_minutes": planned,
        "done_study_minutes": done,
        "progress_percent": round(done / planned * 100),
        "done_sessions": done_sessions,
        "total_sessions": total_sessions,
    }


def _compute_progress_summary(sessions: list[dict], start_date: str, end_date: str) -> dict:
    """Compute week/day progress summary excluding break sessions. Option A: study + habit."""
    total_planned = 0
    total_done = 0
    subject_minutes: dict[str, int] = {}
    done_sessions = 0
    total_sessions = 0

    for s in sessions:
        src = s.get("source", "task")
        # Exclude break sessions from all calculations
        if src == "break":
            continue
        ps = s.get("plannedStart") or s.get("planned_start", "")
        if not ps:
            continue
        day = ps[:10]  # YYYY-MM-DD
        if day < start_date or day > end_date:
            continue
        mins = s.get("minutes", 0)
        total_planned += mins
        total_sessions += 1
        if s.get("status") == "done":
            total_done += mins
            done_sessions += 1
            subj = s.get("subject", "Khác")
            subject_minutes[subj] = subject_minutes.get(subj, 0) + mins

    completion_rate = round(total_done / total_planned * 100) if total_planned > 0 else 0
    return {
        "range": f"{start_date}/{end_date}",
        "total_planned_minutes": total_planned,
        "total_done_minutes": total_done,
        "completion_rate": completion_rate,
        "done_sessions": done_sessions,
        "total_sessions": total_sessions,
        "subject_breakdown": subject_minutes,
    }


# ---------------------------------------------------------------------------
# Student endpoints
# ---------------------------------------------------------------------------

@router.get("/task/{task_id}")
async def get_task_progress(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unified task progress endpoint (used by student & parent with student_id param)."""
    task = await tasks_crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Allow: owner student, or parent with active link
    if task.owner_user_id != current_user.id and current_user.role != "parent":
        raise HTTPException(status_code=403, detail="Không có quyền")
    if current_user.role == "parent":
        link = await parent_crud.get_link(db, current_user.id, task.owner_user_id)
        if not link or link.status != "active":
            raise HTTPException(status_code=403, detail="Không có liên kết")

    plan_result = await db.execute(
        select(PlanRecord)
        .where(PlanRecord.owner_user_id == task.owner_user_id)
        .order_by(PlanRecord.created_at.desc())
        .limit(1)
    )
    plan = plan_result.scalar_one_or_none()
    sessions = plan.sessions if plan else []
    result = _compute_task_progress(sessions, task_id)
    # Fallback if no plan sessions yet
    if result["planned_study_minutes"] == 0:
        done = task.progress_minutes or 0
        planned = task.estimated_minutes or 1
        result.update({
            "planned_study_minutes": planned,
            "done_study_minutes": done,
            "progress_percent": min(100, round(done / planned * 100)),
        })
    return result


@router.get("/summary")
async def get_progress_summary(
    range: str = Query(default="week", description="day|week"),
    student_id: Optional[str] = Query(default=None, description="For parent use"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unified week/day progress summary.
    Student: uses own data.
    Parent: pass student_id (requires active link).
    Excludes break sessions (Option A: study + habit counted together).
    """
    # Resolve which student's data to query
    target_id = current_user.id
    if student_id and student_id != current_user.id:
        if current_user.role != "parent":
            raise HTTPException(status_code=403, detail="Chỉ phụ huynh mới xem được dữ liệu học sinh khác")
        link = await parent_crud.get_link(db, current_user.id, student_id)
        if not link or link.status != "active":
            raise HTTPException(status_code=403, detail="Không có liên kết hợp lệ")
        target_id = student_id

    start_date, end_date = _get_day_range_vn(range)

    plan_result = await db.execute(
        select(PlanRecord)
        .where(PlanRecord.owner_user_id == target_id)
        .order_by(PlanRecord.created_at.desc())
        .limit(1)
    )
    plan = plan_result.scalar_one_or_none()
    sessions = plan.sessions if plan else []
    return _compute_progress_summary(sessions, start_date, end_date)
