"""Shared report computation service.

F: "1 công thức – 1 nguồn dữ liệu – 1 API dùng chung"
Both student UI and parent UI call the same endpoints, which call these functions.

AC2 / AC4: BREAK sessions are excluded from study/habit minutes.
           Only STUDY + HABIT sessions count toward completion %.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

_TZ_VN = timezone(timedelta(hours=7))


def _session_type(s: dict) -> str:
    """Canonical session type: read sessionType if present, else infer from source."""
    st = s.get("sessionType") or s.get("session_type")
    if st:
        return st.upper()
    src = (s.get("source") or "task").lower()
    if src == "break":
        return "BREAK"
    if src == "habit":
        return "HABIT"
    return "STUDY"


def _study_minutes(s: dict) -> int:
    """Return study_minutes field if present; fall back to minutes for STUDY/HABIT."""
    st = _session_type(s)
    if st == "BREAK":
        return 0
    # Use studyMinutes if available (new schema), else minutes
    return s.get("studyMinutes") or s.get("study_minutes") or s.get("minutes", 0)


def _session_date_vn(s: dict) -> str:
    """Return YYYY-MM-DD of session plannedStart in VN timezone."""
    ps = s.get("plannedStart") or s.get("planned_start") or ""
    if not ps:
        return ""
    try:
        dt = datetime.fromisoformat(ps.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_vn = dt.astimezone(_TZ_VN)
        return dt_vn.strftime("%Y-%m-%d")
    except ValueError:
        return ps[:10]


def _parse_week(week_str: str) -> tuple[str, str]:
    """Parse YYYY-Www (ISO week) → (start_date, end_date) as YYYY-MM-DD."""
    # e.g. 2026-W10 → Mon 2026-03-02, Sun 2026-03-08
    m = re.match(r"(\d{4})-W(\d{1,2})$", week_str)
    if not m:
        # Fallback: current week
        today = datetime.now(_TZ_VN).date()
        mon = today - timedelta(days=today.weekday())
        sun = mon + timedelta(days=6)
        return mon.isoformat(), sun.isoformat()
    year, week = int(m.group(1)), int(m.group(2))
    jan4 = date(year, 1, 4)  # Jan 4 is always in week 1
    week1_mon = jan4 - timedelta(days=jan4.weekday())
    mon = week1_mon + timedelta(weeks=week - 1)
    sun = mon + timedelta(days=6)
    return mon.isoformat(), sun.isoformat()


def _build_report_day(sessions: list[dict], target_date: str) -> dict:
    """
    Compute day report for target_date.
    Returns the standard shape expected by frontend and parent/student views.
    """
    study_planned = 0
    study_done = 0
    habit_planned = 0
    habit_done = 0
    break_planned = 0
    items = []

    for s in sessions:
        sdate = _session_date_vn(s)
        if sdate != target_date:
            continue
        st = _session_type(s)
        mins = _study_minutes(s)
        raw_mins = s.get("minutes", 0)  # actual minutes (includes break)
        status = s.get("status", "pending")
        title = s.get("title") or s.get("subject") or st

        if st == "BREAK":
            break_planned += raw_mins
            items.append({
                "title": title,
                "type": "BREAK",
                "minutes": raw_mins,
                "status": "auto",  # BREAK never has done/pending
            })
        elif st == "HABIT":
            habit_planned += mins
            if status == "done":
                habit_done += mins
            items.append({
                "title": title,
                "type": "HABIT",
                "minutes": mins,
                "status": status,
            })
        else:  # STUDY
            study_planned += mins
            if status == "done":
                study_done += mins
            items.append({
                "title": title,
                "type": "STUDY",
                "minutes": mins,
                "status": status,
                "task_id": s.get("taskId") or s.get("task_id"),
            })

    total_planned = study_planned + habit_planned  # excludes BREAK
    total_done = study_done + habit_done
    completion_rate = round(total_done / total_planned, 4) if total_planned > 0 else 0.0

    # Sort items chronologically
    def _sort_key(item_s: dict) -> str:
        return _session_date_vn(item_s) or ""

    # Re-sort by plannedStart from original sessions dict
    session_by_title: dict[str, str] = {}
    for s in sessions:
        k = s.get("title") or ""
        ps = s.get("plannedStart") or s.get("planned_start") or ""
        session_by_title[k] = ps
    items.sort(key=lambda x: session_by_title.get(x["title"], ""))

    return {
        "date": target_date,
        "study_minutes_done": study_done,
        "study_minutes_planned": study_planned,
        "habit_minutes_done": habit_done,
        "habit_minutes_planned": habit_planned,
        "break_minutes_planned": break_planned,
        "total_minutes_done": total_done,
        "total_minutes_planned": total_planned,
        "completion_rate": completion_rate,
        "items": items,
    }


def _build_report_week(sessions: list[dict], start_date: str, end_date: str, week_str: str) -> dict:
    """Compute week report aggregating day-level data."""
    daily: dict[str, dict] = {}
    cursor = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    while cursor.date() <= end.date():
        d = cursor.strftime("%Y-%m-%d")
        daily[d] = _build_report_day(sessions, d)
        cursor += timedelta(days=1)

    study_planned = sum(v["study_minutes_planned"] for v in daily.values())
    study_done = sum(v["study_minutes_done"] for v in daily.values())
    habit_planned = sum(v["habit_minutes_planned"] for v in daily.values())
    habit_done = sum(v["habit_minutes_done"] for v in daily.values())
    break_planned = sum(v["break_minutes_planned"] for v in daily.values())
    total_planned = study_planned + habit_planned
    total_done = study_done + habit_done
    completion_rate = round(total_done / total_planned, 4) if total_planned > 0 else 0.0

    return {
        "week": week_str,
        "start_date": start_date,
        "end_date": end_date,
        "study_minutes_done": study_done,
        "study_minutes_planned": study_planned,
        "habit_minutes_done": habit_done,
        "habit_minutes_planned": habit_planned,
        "break_minutes_planned": break_planned,
        "total_minutes_done": total_done,
        "total_minutes_planned": total_planned,
        "completion_rate": completion_rate,
        "daily": daily,
    }
