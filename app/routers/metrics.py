"""Metrics router — plan quality stats for the frontend dashboard."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import plan as plan_crud
from app.crud import settings as settings_crud
from app.crud import slots as slots_crud
from app.crud import tasks as tasks_crud
from app.database import get_db

router = APIRouter(prefix="/metrics", tags=["metrics"])

TZ_VN = timezone(timedelta(hours=7))


def _parse_date_range(range_key: str, date_str: Optional[str]) -> tuple[datetime, datetime]:
    if date_str:
        try:
            anchor = datetime.fromisoformat(date_str).replace(tzinfo=TZ_VN)
        except ValueError:
            anchor = datetime.now(TZ_VN)
    else:
        anchor = datetime.now(TZ_VN)

    if range_key == "day":
        start = anchor.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif range_key == "month":
        start = anchor.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # first day of next month
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    else:  # week (default)
        # Monday of anchor week
        days_since_monday = anchor.weekday()
        start = (anchor - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(days=7)
    return start, end


def _compute_feasibility(
    sessions_in_range: list,
    range_start: datetime,
    range_end: datetime,
    daily_limit: int,
    total_slot_minutes: int,
    total_demand: int,
) -> tuple[int, list[str]]:
    """Return (score 0-100, [reasons])."""
    reasons: list[str] = []
    score = 100

    # 1. Daily overload check
    by_day: dict[str, int] = {}
    for s in sessions_in_range:
        if s.get("source") == "break":
            continue
        day = (s.get("plannedStart") or s.get("planned_start") or "")[:10]
        by_day[day] = by_day.get(day, 0) + s.get("minutes", 0)

    overloaded_days = [(day, mins) for day, mins in by_day.items() if mins > daily_limit]
    if overloaded_days:
        penalty = min(30, len(overloaded_days) * 10)
        score -= penalty
        reasons.append(
            f"Quá tải: {len(overloaded_days)} ngày vượt {daily_limit}p/ngày "
            f"(max {max(v for _, v in overloaded_days)}p)"
        )

    # 2. Slot capacity vs demand
    if total_slot_minutes > 0 and total_demand > total_slot_minutes:
        shortage_pct = (total_demand - total_slot_minutes) / total_demand
        penalty = min(25, int(shortage_pct * 40))
        score -= penalty
        reasons.append(
            f"Thiếu slot: cần {total_demand}p nhưng chỉ có {total_slot_minutes}p rảnh"
        )

    # 3. Break buffer check — penalise if no break sessions at all on loaded days
    break_days = {
        (s.get("plannedStart") or "")[:10]
        for s in sessions_in_range
        if s.get("source") == "break"
    }
    focus_days = set(by_day.keys())
    missing_breaks = focus_days - break_days
    if missing_breaks:
        penalty = min(20, len(missing_breaks) * 5)
        score -= penalty
        reasons.append(f"Thiếu session nghỉ trong {len(missing_breaks)} ngày")

    # 4. Deadline pressure — tasks due within 48h and still unscheduled → handled upstream
    score = max(0, min(100, score))
    # Leave reasons empty when no issues — frontend shows a positive banner in that case
    return score, reasons


@router.get("/plan")
async def get_plan_metrics(
    range: str = Query(default="week", pattern="^(day|week|month)$"),
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD anchor date"),
    db: AsyncSession = Depends(get_db),
):
    """Return completion rate, feasibility score + reasons for the given range."""
    range_start, range_end = _parse_date_range(range, date)

    plan = await plan_crud.get_latest_plan(db)
    settings_row = await settings_crud.get_settings(db)
    slots_rows = await slots_crud.list_slots(db)
    tasks_rows = await tasks_crud.list_tasks(db)

    if plan is None:
        return {
            "range": range,
            "rangeStart": range_start.isoformat(),
            "rangeEnd": range_end.isoformat(),
            "totalSessions": 0,
            "doneSessions": 0,
            "completionRate": 0.0,
            "feasibilityScore": 0,
            "feasibilityReasons": ["Chưa có kế hoạch — hãy tạo kế hoạch trước."],
            "planVersion": None,
        }

    all_sessions: list = plan.sessions or []
    sessions_in_range = [
        s for s in all_sessions
        if s.get("source") != "break"
        and range_start.isoformat()[:10] <= (s.get("plannedStart") or "")[:10] < range_end.isoformat()[:10]
    ]

    total = len(sessions_in_range)
    done = sum(1 for s in sessions_in_range if s.get("status") == "done")
    completion_rate = round(done / total * 100, 1) if total > 0 else 0.0

    # Total slot minutes across days in range (approximate weekday coverage)
    total_slot_minutes = sum(s.capacity_minutes for s in slots_rows)
    total_demand = sum(
        max(0, t.estimated_minutes - t.progress_minutes)
        for t in tasks_rows
    )

    feasibility_score, feasibility_reasons = _compute_feasibility(
        sessions_in_range=sessions_in_range,
        range_start=range_start,
        range_end=range_end,
        daily_limit=settings_row.daily_limit_minutes,
        total_slot_minutes=total_slot_minutes,
        total_demand=total_demand,
    )

    return {
        "range": range,
        "rangeStart": range_start.isoformat(),
        "rangeEnd": range_end.isoformat(),
        "totalSessions": total,
        "doneSessions": done,
        "completionRate": completion_rate,
        "feasibilityScore": feasibility_score,
        "feasibilityReasons": feasibility_reasons,
        "planVersion": plan.plan_version,
    }
