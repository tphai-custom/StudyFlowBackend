"""Port of generatePlan.ts — core scheduling algorithm."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.planner.clean_slots import clean_slots
from app.schemas.free_slot import FreeSlotSchema
from app.schemas.habit import HabitSchema
from app.schemas.plan import PlanRecordSchema, PlanSuggestionSchema, SessionSchema
from app.schemas.settings import AppSettingsSchema
from app.schemas.task import TaskSchema

MIN_SESSION_MINUTES = 25
MAX_SESSION_MINUTES = 120
TZ_OFFSET = timezone(timedelta(hours=7))  # UTC+7


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

@dataclass
class DaySegment:
    start: datetime
    end: datetime
    used: int = 0


@dataclass
class DayBucket:
    iso_date: str
    weekday: int
    segments: list[DaySegment] = field(default_factory=list)
    allowed_minutes: int = 0
    used: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_datetime(iso_date: str, time: str) -> datetime:
    return datetime.fromisoformat(f"{iso_date}T{time}:00+07:00")


def _start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _diff_minutes(a: datetime, b: datetime) -> int:
    return int((b - a).total_seconds() // 60)


def _as_vn_aware(iso: str) -> datetime:
    """Normalize any ISO datetime string to a timezone-aware datetime in UTC+7."""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ_OFFSET)


def _add_minutes(dt: datetime, minutes: int) -> datetime:
    return dt + timedelta(minutes=minutes)


# ---------------------------------------------------------------------------
# Build day buckets
# ---------------------------------------------------------------------------

def _build_buckets(
    now: datetime,
    end: datetime,
    slots: list[FreeSlotSchema],
    settings: AppSettingsSchema,
) -> list[DayBucket]:
    buckets: list[DayBucket] = []
    cursor = _start_of_day(now)
    end_of_window = _start_of_day(end)

    while cursor <= end_of_window:
        iso_date = cursor.strftime("%Y-%m-%d")
        weekday = cursor.weekday()  # Python: 0=Monday … 6=Sunday
        # Normalise: FreeSlot weekday uses JS convention (0=Sunday)
        js_weekday = (weekday + 1) % 7
        day_slots = [s for s in slots if s.weekday == js_weekday]

        segments: list[DaySegment] = []
        for slot in day_slots:
            seg_start = _to_datetime(iso_date, slot.start_time)
            if cursor.date() == now.date():
                seg_start = max(seg_start, now)
            seg_end = _to_datetime(iso_date, slot.end_time)
            segments.append(DaySegment(start=seg_start, end=seg_end))

        total_minutes = sum(
            max(0, _diff_minutes(seg.start, seg.end)) for seg in segments
        )
        allowed = max(
            0,
            min(
                settings.daily_limit_minutes,
                int(total_minutes * (1 - settings.buffer_percent)),
            ),
        )
        buckets.append(
            DayBucket(
                iso_date=iso_date,
                weekday=js_weekday,
                segments=segments,
                allowed_minutes=allowed,
            )
        )
        cursor += timedelta(days=1)

    return buckets


# ---------------------------------------------------------------------------
# Prioritise tasks
# ---------------------------------------------------------------------------

def _prioritize_tasks(tasks: list[TaskSchema]) -> list[TaskSchema]:
    return sorted(
        tasks,
        key=lambda t: (
            _as_vn_aware(t.deadline).timestamp(),
            -(t.importance or 0),
            -t.difficulty,
            -t.estimated_minutes,
        ),
    )


# ---------------------------------------------------------------------------
# Allocate time from a bucket
# ---------------------------------------------------------------------------

def _take_from_bucket(
    bucket: DayBucket,
    remaining: int,
    chunk_preference: int,
    *,
    allow_shorter_than_min: bool = False,
) -> Optional[dict]:
    if bucket.used >= bucket.allowed_minutes:
        return None
    for segment in bucket.segments:
        seg_capacity = max(0, _diff_minutes(segment.start, segment.end) - segment.used)
        if seg_capacity <= 0:
            continue
        remaining_today = bucket.allowed_minutes - bucket.used
        chunk = min(chunk_preference, remaining, seg_capacity, MAX_SESSION_MINUTES, remaining_today)
        if not allow_shorter_than_min and chunk < MIN_SESSION_MINUTES and remaining > MIN_SESSION_MINUTES:
            continue
        minutes = chunk if chunk != 0 else min(remaining, seg_capacity)
        session_start = _add_minutes(segment.start, segment.used)
        session_end = _add_minutes(session_start, minutes)
        segment.used += minutes
        bucket.used += minutes
        return {
            "session_start": session_start,
            "session_end": session_end,
            "minutes": minutes,
        }
    return None


# ---------------------------------------------------------------------------
# Schedule habits
# ---------------------------------------------------------------------------

def _schedule_habits(
    buckets: list[DayBucket],
    habits: list[HabitSchema],
    settings: AppSettingsSchema,
    plan_version: int,
) -> tuple[list[SessionSchema], list[PlanSuggestionSchema]]:
    habit_sessions: list[SessionSchema] = []
    suggestions: list[PlanSuggestionSchema] = []

    for bucket in buckets:
        for habit in habits:
            should_schedule = habit.cadence == "daily" or (
                habit.cadence == "weekly" and habit.weekday == bucket.weekday
            )
            if not should_schedule:
                continue

            remaining = habit.minutes
            allocation = _take_from_bucket(
                bucket, remaining, habit.minutes, allow_shorter_than_min=True
            )
            if not allocation:
                suggestions.append(
                    PlanSuggestionSchema(
                        type="increase_free_time",
                        message=f'Không đủ slot cho habit "{habit.name}" vào {bucket.iso_date}.',
                    )
                )
                continue

            while allocation and remaining > 0:
                mins = allocation["minutes"]
                habit_sessions.append(
                    SessionSchema(
                        id=str(uuid.uuid4()),
                        habitId=habit.id,
                        source="habit",
                        subject="Thói quen",
                        title=habit.name,
                        plannedStart=allocation["session_start"].isoformat(),
                        plannedEnd=allocation["session_end"].isoformat(),
                        minutes=mins,
                        bufferMinutes=round(mins * settings.buffer_percent * 0.5),
                        status="pending",
                        successCriteria=[f"Duy trì {mins} phút"],
                        planVersion=plan_version,
                    )
                )
                remaining -= mins
                allocation = (
                    _take_from_bucket(
                        bucket, remaining, habit.minutes, allow_shorter_than_min=True
                    )
                    if remaining > 0
                    else None
                )

    return habit_sessions, suggestions


# ---------------------------------------------------------------------------
# Insert breaks between consecutive focus sessions
# ---------------------------------------------------------------------------

def _apply_breaks(
    focus_sessions: list[SessionSchema],
    settings: AppSettingsSchema,
    plan_version: int,
) -> list[SessionSchema]:
    if not focus_sessions:
        return []

    by_day: dict[str, list[SessionSchema]] = {}
    for session in focus_sessions:
        key = session.planned_start[:10]
        by_day.setdefault(key, []).append(session)

    result: list[SessionSchema] = []
    rest_base = settings.break_preset.rest or 5
    break_label = settings.break_preset.label or "Break"

    for day_sessions in by_day.values():
        ordered = sorted(day_sessions, key=lambda s: s.planned_start)
        offset = 0
        for i, session in enumerate(ordered):
            shifted_start = _add_minutes(
                datetime.fromisoformat(session.planned_start), offset
            )
            shifted_end = _add_minutes(
                datetime.fromisoformat(session.planned_end), offset
            )
            adjusted = SessionSchema(
                **{
                    **session.model_dump(by_alias=True),
                    "plannedStart": shifted_start.isoformat(),
                    "plannedEnd": shifted_end.isoformat(),
                }
            )
            result.append(adjusted)

            if session.source == "break":
                continue

            next_session = ordered[i + 1] if i + 1 < len(ordered) else None
            if not next_session or next_session.source == "break":
                continue

            gap_seconds = (
                datetime.fromisoformat(next_session.planned_start)
                - datetime.fromisoformat(session.planned_end)
            ).total_seconds()
            consecutive = gap_seconds <= 5 * 60
            if not consecutive:
                continue

            contiguous_load = session.minutes + next_session.minutes
            rest_minutes = rest_base + 5 if contiguous_load >= 90 else rest_base
            break_start = shifted_end
            break_end = _add_minutes(break_start, rest_minutes)
            result.append(
                SessionSchema(
                    id=str(uuid.uuid4()),
                    source="break",
                    subject="Nghỉ",
                    title=break_label,
                    plannedStart=break_start.isoformat(),
                    plannedEnd=break_end.isoformat(),
                    minutes=rest_minutes,
                    bufferMinutes=0,
                    status="pending",
                    successCriteria=["Nghỉ ngơi"],
                    planVersion=plan_version,
                )
            )
            offset += rest_minutes

    return sorted(result, key=lambda s: s.planned_start)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_plan(
    tasks: list[TaskSchema],
    free_slots: list[FreeSlotSchema],
    habits: list[HabitSchema],
    settings: AppSettingsSchema,
    now_iso: str,
    previous_plan_version: Optional[int] = None,
) -> PlanRecordSchema:
    now = _as_vn_aware(now_iso)
    cleaned = clean_slots(free_slots)
    clean_slot_list: list[FreeSlotSchema] = cleaned["slots"]
    warnings: list[str] = cleaned["warnings"]
    plan_version = (previous_plan_version or 0) + 1

    future_tasks = [t for t in tasks if _as_vn_aware(t.deadline) > now]
    prioritized = _prioritize_tasks(future_tasks)

    latest_deadline = now
    for task in prioritized:
        dl = _as_vn_aware(task.deadline)
        if dl > latest_deadline:
            latest_deadline = dl

    if not prioritized and habits:
        latest_deadline = now + timedelta(days=14)

    buckets = [
        b
        for b in _build_buckets(now, latest_deadline, clean_slot_list, settings)
        if b.segments
    ]

    habit_sessions, habit_suggestions = _schedule_habits(
        buckets, habits, settings, plan_version
    )

    total_capacity = sum(b.allowed_minutes for b in buckets)
    total_demand = sum(
        max(0, t.estimated_minutes - t.progress_minutes) for t in prioritized
    )

    suggestions: list[PlanSuggestionSchema] = list(habit_suggestions)
    if total_capacity < total_demand:
        suggestions.append(
            PlanSuggestionSchema(
                type="increase_free_time",
                message="Không đủ giờ rảnh để hoàn thành toàn bộ nhiệm vụ. Hãy thêm slot hoặc tăng daily limit.",
            )
        )
    for w in warnings:
        suggestions.append(PlanSuggestionSchema(type="increase_free_time", message=w))

    sessions: list[SessionSchema] = list(habit_sessions)
    unscheduled: list[TaskSchema] = []
    focus_chunk = settings.break_preset.focus or 45

    for task in prioritized:
        remaining = max(0, task.estimated_minutes - task.progress_minutes)
        deadline = _as_vn_aware(task.deadline)
        eligible_buckets = [
            b
            for b in buckets
            if datetime.fromisoformat(f"{b.iso_date}T23:59:00+07:00") <= deadline
        ]
        if not eligible_buckets:
            unscheduled.append(task)
            suggestions.append(
                PlanSuggestionSchema(
                    type="increase_free_time",
                    message=f'Task "{task.title}" không nằm trong bất kỳ slot nào.',
                )
            )
            continue

        base_criteria = (
            task.success_criteria
            if task.success_criteria
            else ["Hoàn thành buổi học"]
        )
        checklist = (
            [item.strip() for item in task.content_focus.splitlines() if item.strip()]
            if task.content_focus
            else None
        )

        def allocate(
            bucket: DayBucket,
            minutes_needed: int,
            chunk_pref: int,
            milestone_title: Optional[str] = None,
        ) -> int:
            nonlocal remaining
            local_remaining = minutes_needed
            attempt = _take_from_bucket(
                bucket,
                local_remaining,
                chunk_pref,
                allow_shorter_than_min=bool(milestone_title),
            )
            while attempt and local_remaining > 0:
                mins = attempt["minutes"]
                sessions.append(
                    SessionSchema(
                        id=str(uuid.uuid4()),
                        taskId=task.id,
                        source="task",
                        subject=task.subject,
                        title=task.title,
                        plannedStart=attempt["session_start"].isoformat(),
                        plannedEnd=attempt["session_end"].isoformat(),
                        minutes=mins,
                        bufferMinutes=round(mins * settings.buffer_percent),
                        status="pending",
                        checklist=checklist,
                        successCriteria=base_criteria,
                        milestoneTitle=milestone_title,
                        planVersion=plan_version,
                    )
                )
                remaining -= mins
                local_remaining -= mins
                attempt = (
                    _take_from_bucket(
                        bucket,
                        local_remaining,
                        chunk_pref,
                        allow_shorter_than_min=bool(milestone_title),
                    )
                    if local_remaining > 0
                    else None
                )
            return local_remaining

        if task.milestones:
            for milestone in task.milestones:
                ms_remaining = min(milestone.minutes_estimate, remaining)
                for bucket in eligible_buckets:
                    if ms_remaining <= 0:
                        break
                    ms_remaining = allocate(
                        bucket,
                        ms_remaining,
                        milestone.minutes_estimate,
                        milestone.title,
                    )
        else:
            for bucket in eligible_buckets:
                if remaining <= 0:
                    break
                allocate(bucket, remaining, focus_chunk)

        if remaining > 0:
            unscheduled.append(task)
            suggestions.append(
                PlanSuggestionSchema(
                    type="reduce_duration",
                    message=f'Nhiệm vụ "{task.title}" thiếu {remaining} phút. Giảm thời lượng hoặc thêm slot.',
                )
            )

    sessions_with_breaks = _apply_breaks(sessions, settings, plan_version)
    generated_at = datetime.utcnow().isoformat()

    return PlanRecordSchema(
        id=str(uuid.uuid4()),
        planVersion=plan_version,
        sessions=sessions_with_breaks,
        unscheduledTasks=[t.model_dump(by_alias=True) for t in unscheduled],
        suggestions=suggestions,
        generatedAt=generated_at,
    )
