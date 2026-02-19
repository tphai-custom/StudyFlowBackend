"""
Core plan generation algorithm.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from app.planner.clean_slots import clean_slots, _time_to_minutes

# Vietnam offset
VN_OFFSET = timedelta(hours=7)
VN_TZ = timezone(VN_OFFSET)


def _now_vn() -> datetime:
    return datetime.now(tz=VN_TZ)


def _parse_iso(s: str) -> datetime:
    """Parse ISO string to aware datetime (UTC)."""
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def _to_iso(dt: datetime) -> str:
    """Convert datetime to ISO string with Z suffix (UTC)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def _slot_weekday_python(weekday_js: int) -> int:
    """Convert JS weekday (0=Sunday) to Python weekday (0=Monday)."""
    return (weekday_js - 1) % 7


def generate_plan(
    tasks: List[Dict[str, Any]],
    free_slots: List[Dict[str, Any]],
    habits: List[Dict[str, Any]],
    settings: Dict[str, Any],
    current_plan_version: int,
) -> Dict[str, Any]:
    now_vn = _now_vn()
    plan_version = current_plan_version + 1

    daily_limit = settings.get("dailyLimitMinutes", 240)
    buffer_pct = settings.get("bufferPercent", 0.1)
    break_preset = settings.get("breakPreset", {"focus": 45, "rest": 10})
    focus_chunk = break_preset.get("focus", 45)
    rest_minutes = break_preset.get("rest", 10)

    # Cap chunk size
    chunk_size = min(max(focus_chunk, 25), 120)

    # Step 2: Filter tasks with deadline in the future
    active_tasks = []
    for t in tasks:
        try:
            deadline_dt = _parse_iso(t["deadline"])
            if deadline_dt > datetime.now(tz=timezone.utc):
                active_tasks.append(t)
        except Exception:
            active_tasks.append(t)

    # Step 3: Clean free slots
    cleaned_slots = clean_slots(free_slots)

    # Step 4: Determine planning horizon
    latest_deadline: Optional[datetime] = None
    for t in active_tasks:
        try:
            dl = _parse_iso(t["deadline"])
            if latest_deadline is None or dl > latest_deadline:
                latest_deadline = dl
        except Exception:
            pass

    if latest_deadline is None:
        end_date = now_vn + timedelta(days=14)
    else:
        end_date = latest_deadline.astimezone(VN_TZ)

    # Ensure we plan at least 1 day
    num_days = max((end_date.date() - now_vn.date()).days + 1, 1)

    # Step 5: Build day buckets
    # day_buckets: list of {date, slots: [{start_min, end_min, capacity}]}
    day_buckets = []
    for i in range(num_days):
        day_date = now_vn.date() + timedelta(days=i)
        # Python weekday: 0=Monday; JS weekday: 0=Sunday
        py_weekday = day_date.weekday()
        js_weekday = (py_weekday + 1) % 7

        day_slot_segments = []
        for s in cleaned_slots:
            if s["weekday"] == js_weekday:
                start_min = _time_to_minutes(s["startTime"])
                end_min = _time_to_minutes(s["endTime"])
                day_slot_segments.append({"start_min": start_min, "end_min": end_min})

        day_slot_segments.sort(key=lambda x: x["start_min"])
        total_slot_minutes = sum(seg["end_min"] - seg["start_min"] for seg in day_slot_segments)
        allowed = min(daily_limit, int(total_slot_minutes * (1 - buffer_pct)))

        day_buckets.append({
            "date": day_date,
            "js_weekday": js_weekday,
            "segments": day_slot_segments,
            "total_slot_minutes": total_slot_minutes,
            "allowed_minutes": allowed,
            "used_minutes": 0,
            "sessions": [],
            "last_session_end_min": None,
        })

    sessions: List[Dict[str, Any]] = []

    # Step 6: Schedule habits
    for habit in habits:
        h_minutes = habit.get("minutes", 30)
        h_cadence = habit.get("cadence", "daily")
        h_weekday_js = habit.get("weekday")

        for bucket in day_buckets:
            if h_cadence == "weekly":
                if h_weekday_js is None or bucket["js_weekday"] != h_weekday_js:
                    continue

            # Try to fit this habit into the bucket
            placed = _place_session_in_bucket(
                bucket=bucket,
                duration=h_minutes,
                rest_minutes=rest_minutes,
                session_data={
                    "id": str(uuid.uuid4()),
                    "habitId": habit["id"],
                    "taskId": None,
                    "source": "habit",
                    "subject": habit.get("name", "Habit"),
                    "title": habit.get("name", "Habit"),
                    "minutes": h_minutes,
                    "bufferMinutes": 0,
                    "status": "pending",
                    "checklist": None,
                    "successCriteria": None,
                    "milestoneTitle": None,
                    "completedAt": None,
                    "planVersion": plan_version,
                },
            )
            if placed:
                sessions.append(placed)

    # Step 7: Sort tasks by deadline ASC, importance DESC, difficulty DESC, estimatedMinutes DESC
    def task_sort_key(t: Dict[str, Any]):
        try:
            dl = _parse_iso(t["deadline"]).timestamp()
        except Exception:
            dl = float("inf")
        importance = -(t.get("importance") or 0)
        difficulty = -(t.get("difficulty") or 0)
        est = -(t.get("estimatedMinutes") or 0)
        return (dl, importance, difficulty, est)

    sorted_tasks = sorted(active_tasks, key=task_sort_key)

    unscheduled_tasks = []
    suggestions = []

    # Step 8-10: Schedule tasks
    for task in sorted_tasks:
        try:
            deadline_dt = _parse_iso(task["deadline"]).astimezone(VN_TZ)
        except Exception:
            deadline_dt = None

        remaining_minutes = task.get("estimatedMinutes", 60) - task.get("progressMinutes", 0)
        remaining_minutes = max(remaining_minutes, 0)

        if remaining_minutes == 0:
            continue

        milestones = task.get("milestones") or []
        task_sessions_placed = 0

        if milestones:
            for milestone in milestones:
                ms_minutes = milestone.get("minutesEstimate", chunk_size)
                ms_remaining = ms_minutes
                for bucket in day_buckets:
                    if ms_remaining <= 0:
                        break
                    if deadline_dt and bucket["date"] > deadline_dt.date():
                        break
                    while ms_remaining > 0:
                        session_min = min(ms_remaining, chunk_size, 120)
                        if session_min < 25:
                            break
                        placed = _place_session_in_bucket(
                            bucket=bucket,
                            duration=session_min,
                            rest_minutes=rest_minutes,
                            session_data={
                                "id": str(uuid.uuid4()),
                                "taskId": task["id"],
                                "habitId": None,
                                "source": "task",
                                "subject": task.get("subject", ""),
                                "title": task.get("title", ""),
                                "minutes": session_min,
                                "bufferMinutes": rest_minutes,
                                "status": "pending",
                                "checklist": None,
                                "successCriteria": task.get("successCriteria"),
                                "milestoneTitle": milestone.get("title"),
                                "completedAt": None,
                                "planVersion": plan_version,
                            },
                        )
                        if placed:
                            sessions.append(placed)
                            task_sessions_placed += 1
                            ms_remaining -= session_min
                        else:
                            break
        else:
            task_remaining = remaining_minutes
            for bucket in day_buckets:
                if task_remaining <= 0:
                    break
                if deadline_dt and bucket["date"] > deadline_dt.date():
                    break
                while task_remaining > 0:
                    session_min = min(task_remaining, chunk_size, 120)
                    if session_min < 25:
                        break
                    placed = _place_session_in_bucket(
                        bucket=bucket,
                        duration=session_min,
                        rest_minutes=rest_minutes,
                        session_data={
                            "id": str(uuid.uuid4()),
                            "taskId": task["id"],
                            "habitId": None,
                            "source": "task",
                            "subject": task.get("subject", ""),
                            "title": task.get("title", ""),
                            "minutes": session_min,
                            "bufferMinutes": rest_minutes,
                            "status": "pending",
                            "checklist": None,
                            "successCriteria": task.get("successCriteria"),
                            "milestoneTitle": None,
                            "completedAt": None,
                            "planVersion": plan_version,
                        },
                    )
                    if placed:
                        sessions.append(placed)
                        task_sessions_placed += 1
                        task_remaining -= session_min
                    else:
                        break

            if task_remaining > 0:
                unscheduled_tasks.append(task)
                suggestions.append({
                    "type": "unscheduled",
                    "message": f"Không đủ thời gian cho: {task.get('title', '')}",
                })

    generated_at = _to_iso(datetime.now(tz=timezone.utc))
    return {
        "planVersion": plan_version,
        "sessions": sessions,
        "unscheduledTasks": unscheduled_tasks,
        "suggestions": suggestions,
        "generatedAt": generated_at,
    }


def _place_session_in_bucket(
    bucket: Dict[str, Any],
    duration: int,
    rest_minutes: int,
    session_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Try to fit a session of `duration` minutes into the bucket.
    Returns the session dict if placed, else None.
    Adds a break session before if there was a previous session.
    """
    if bucket["allowed_minutes"] - bucket["used_minutes"] < duration:
        return None

    # Find a segment with enough room
    for seg in bucket["segments"]:
        seg_start = seg["start_min"]
        seg_end = seg["end_min"]
        seg_capacity = seg_end - seg_start

        # Current cursor within segment
        cursor = seg.get("cursor_min", seg_start)

        # Add rest gap if there was a prior session in this segment
        if seg.get("last_end_min") is not None:
            cursor = seg["last_end_min"] + rest_minutes

        if cursor + duration > seg_end:
            continue

        # Place the session
        session_start_min = cursor
        session_end_min = cursor + duration

        day_date = bucket["date"]
        start_dt = _day_min_to_dt(day_date, session_start_min)
        end_dt = _day_min_to_dt(day_date, session_end_min)

        seg["cursor_min"] = session_end_min
        seg["last_end_min"] = session_end_min
        bucket["used_minutes"] += duration
        bucket["last_session_end_min"] = session_end_min

        return {
            **session_data,
            "plannedStart": _to_iso(start_dt),
            "plannedEnd": _to_iso(end_dt),
        }

    return None


def _day_min_to_dt(day_date, minutes: int) -> datetime:
    """Convert a date + minutes-since-midnight (in VN time) to UTC datetime."""
    vn_dt = datetime(
        day_date.year,
        day_date.month,
        day_date.day,
        minutes // 60,
        minutes % 60,
        0,
        tzinfo=VN_TZ,
    )
    return vn_dt.astimezone(timezone.utc)
