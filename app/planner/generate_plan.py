"""Port of generatePlan.ts — core scheduling algorithm."""
from __future__ import annotations

import re
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
# Urgency × StyleWeight priority system (C/D)
# ---------------------------------------------------------------------------

URGENT_DAYS_THRESHOLD = 3  # Days left where "min 1 session/day" kicks in


def _days_until(deadline_dt: datetime, ref_dt: datetime) -> int:
    """Number of calendar days from ref_dt to deadline_dt (min 0)."""
    delta = (deadline_dt.date() - ref_dt.date()).days
    return max(0, delta)


def _style_weight(progress: float, style: str) -> float:
    """
    C3: Style weight based on progress through [today .. deadline] window.
    progress ∈ [0, 1]
    front-load  → weight high early
    balanced    → constant 1.0
    deadline-loaded → weight high late
    """
    if style == "front-load":
        return (1.0 - progress) ** 2 + 0.2
    elif style == "deadline-loaded":
        return progress ** 2 + 0.2
    else:  # balanced
        return 1.0


def _task_priority(
    task: TaskSchema, ref_dt: datetime, remaining_minutes: int
) -> float:
    """
    C1/C2: priority = urgency_score * style_weight
    urgency_score = remaining_minutes / days_left  (higher = more urgent)
    """
    days_left = max(1, _days_until(_as_vn_aware(task.deadline), ref_dt) + 1)
    urgency_score = remaining_minutes / days_left

    deadline_dt = _as_vn_aware(task.deadline)
    start_dt = ref_dt  # today is the start of our window
    total_window = max(1, _days_until(deadline_dt, start_dt))
    # progress = 0 at ref_dt (start of window), 1 at deadline
    progress = 0.0  # relative to today; used for initial triage

    style = getattr(task, "scheduling_style", "balanced")
    sw = _style_weight(progress, style)

    return urgency_score * sw


def _bucket_task_priority(
    task: TaskSchema, bucket: "DayBucket", now: datetime, remaining_minutes: int
) -> float:
    """Per-bucket priority: urgency (based on days from bucket date to deadline) × style_weight."""
    deadline_dt = _as_vn_aware(task.deadline)
    bucket_dt = datetime.fromisoformat(f"{bucket.iso_date}T00:00:00+07:00")

    days_left_from_bucket = max(1, _days_until(deadline_dt, bucket_dt) + 1)
    urgency_score = remaining_minutes / days_left_from_bucket

    total_window = max(1, _days_until(deadline_dt, now))
    elapsed = max(0, _days_until(bucket_dt, now))
    progress = min(1.0, elapsed / total_window) if total_window > 0 else 0.0

    style = getattr(task, "scheduling_style", "balanced")
    sw = _style_weight(progress, style)

    return urgency_score * sw


# ---------------------------------------------------------------------------
# Prioritise tasks (initial sort — urgency-aware)
# ---------------------------------------------------------------------------

def _prioritize_tasks(tasks: list[TaskSchema], now: datetime | None = None) -> list[TaskSchema]:
    """
    Sort tasks: parent/locked first, then by urgency = remaining/days_left * style_weight.
    This ensures a task with a near deadline is never buried behind a far-deadline task.
    Falls back to deadline-ASC as a secondary key.
    """
    if now is None:
        now = datetime.now(tz=TZ_OFFSET)

    def sort_key(t: TaskSchema):
        source_priority = (
            0 if (getattr(t, "source", "student") == "parent" and getattr(t, "locked", False)) else
            1 if getattr(t, "source", "student") == "parent" else 2
        )
        remaining = max(1, _effective_minutes(t) - t.progress_minutes)
        # Higher priority = lower sort key → negate urgency
        urgency = _task_priority(t, now, remaining)
        return (
            source_priority,
            -urgency,  # more urgent first
            _as_vn_aware(t.deadline).timestamp(),
        )

    return sorted(tasks, key=sort_key)


# ---------------------------------------------------------------------------
# Resolve effective_minutes based on duration_mode
# ---------------------------------------------------------------------------

def _effective_minutes(task: TaskSchema) -> int:
    """C3: Use target_minutes if available (computed field). Otherwise compute inline.

    target_minutes is the hard cap: sum(study_minutes) must equal this value.
    """
    # Prefer the pre-computed target_minutes field (added in n2o3p4q5r6s7 migration)
    target = getattr(task, "target_minutes", None)
    if target and target > 0:
        return target

    # Fallback: compute inline (for old/unpatched tasks)
    duration_mode = getattr(task, "duration_mode", "estimate")
    if duration_mode == "exact":
        exact = getattr(task, "duration_minutes_exact", None)
        if exact and exact > 0:
            return exact
    # estimate: clamp mid to [min, max]
    t_min = getattr(task, "duration_minutes_min", None)
    t_max = getattr(task, "duration_minutes_max", None)
    if t_min and t_max and t_min > 0 and t_max > 0:
        base = round((t_min + t_max) / 2)
        return max(t_min, min(t_max, base))
    # final fallback
    return task.estimated_minutes


# ---------------------------------------------------------------------------
# Sort eligible buckets by scheduling style
# ---------------------------------------------------------------------------

def _sort_buckets_by_style(
    buckets: list[DayBucket],
    deadline: datetime,
    style: str,
) -> list[DayBucket]:
    """
    front-load    → earliest days first (index ASC)
    balanced      → most remaining capacity first, tie-break by date
    deadline-loaded → days closest to (but not past) deadline first
    """
    if style == "front-load":
        return sorted(buckets, key=lambda b: b.iso_date)
    elif style == "deadline-loaded":
        # Sort descending by date (closest to deadline first), but never past it
        deadline_str = deadline.strftime("%Y-%m-%d")
        return sorted(
            buckets,
            key=lambda b: (
                # higher = further from deadline (deprioritized)
                (ord(deadline_str[5]) - ord(b.iso_date[5])) * 10000  # coarse month diff
                + abs((b.iso_date > deadline_str) * 999999),  # penalise past deadline
            ),
            reverse=True,
        )
    else:  # balanced
        # Prefer days with most remaining capacity (allowed - used), tie by date
        return sorted(
            buckets,
            key=lambda b: (
                -(b.allowed_minutes - b.used),  # most free first
                b.iso_date,                      # tie: earlier date first
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
        # Fix blank-day bug: allow short "tail" sessions when nearly done
        # (remaining <= MIN_SESSION_MINUTES means we're almost done — don't skip)
        tail_session = remaining <= MIN_SESSION_MINUTES
        if not allow_shorter_than_min and not tail_session and chunk < MIN_SESSION_MINUTES and remaining > MIN_SESSION_MINUTES:
            continue
        minutes = chunk if chunk != 0 else min(remaining, seg_capacity)
        if minutes <= 0:
            continue
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
                buf = round(mins * settings.buffer_percent * 0.5)
                habit_sessions.append(
                    SessionSchema(
                        id=str(uuid.uuid4()),
                        habitId=habit.id,
                        source="habit",
                        sessionType="HABIT",
                        subject="Thói quen",
                        title=habit.name,
                        plannedStart=allocation["session_start"].isoformat(),
                        plannedEnd=allocation["session_end"].isoformat(),
                        minutes=mins,
                        studyMinutes=mins,
                        occupiedMinutes=mins + buf,
                        bufferMinutes=buf,
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
                    sessionType="BREAK",
                    subject="Nghỉ",
                    title=break_label,
                    plannedStart=break_start.isoformat(),
                    plannedEnd=break_end.isoformat(),
                    minutes=rest_minutes,
                    studyMinutes=0,
                    occupiedMinutes=rest_minutes,
                    bufferMinutes=0,
                    status="auto",
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
    prioritized = _prioritize_tasks(future_tasks, now)

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
        max(0, _effective_minutes(t) - t.progress_minutes) for t in prioritized
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

    # ── Build per-task remaining-minutes tracker ──────────────────────────
    task_remaining: dict[str, int] = {}
    task_criteria: dict[str, list[str]] = {}
    task_checklist: dict[str, Optional[list[str]]] = {}
    for t in prioritized:
        effective_total = _effective_minutes(t)
        task_remaining[t.id] = max(0, effective_total - t.progress_minutes)
        task_criteria[t.id] = t.success_criteria if t.success_criteria else ["Hoàn thành buổi học"]
        task_checklist[t.id] = (
            [item.strip() for item in t.content_focus.splitlines() if item.strip()]
            if t.content_focus
            else None
        )

    # ── Pre-compute balanced quotas: 3 days/week, evenly spread ─────────────
    # For each balanced task, compute how many minutes to schedule per study-day.
    # Formula: weeks = ceil(days_until_deadline / 7), study_days = weeks × 3,
    #          minutes_per_day = ceil(total_remaining / study_days)
    balanced_quota: dict[str, int] = {}   # task_id → target minutes per study day
    balanced_week_usage: dict[tuple, int] = {}  # (task_id, week_idx) → # days used this week

    for t in prioritized:
        style = getattr(t, "scheduling_style", "balanced")
        if style != "balanced":
            continue
        rm = task_remaining.get(t.id, 0)
        if rm <= 0:
            continue
        deadline_dt = _as_vn_aware(t.deadline)
        days_until_dl = max(1, _days_until(deadline_dt, now))
        num_weeks = max(1, (days_until_dl + 6) // 7)       # ceil(days / 7)
        total_slots = num_weeks * 3                         # 3 days per week
        raw_quota = max(
            MIN_SESSION_MINUTES,
            (rm + total_slots - 1) // total_slots,          # ceil division
        )
        # Round up to the nearest 10 minutes (e.g. 14 → 20, 34 → 40)
        balanced_quota[t.id] = ((raw_quota + 9) // 10) * 10

    # ── Pre-compute deadline-loaded quotas: 30% first half, 70% second half ──
    # First half  (now → midpoint) : 30% of remaining minutes, 3 days/week
    # Second half (midpoint → deadline): 70% of remaining minutes, 3 days/week
    # Both halves: per-day quota rounded up to nearest 10 min
    deadline_loaded_quota: dict[str, dict] = {}  # task_id → {midpoint, q1, q2}
    deadline_week_usage: dict[tuple, int] = {}   # (task_id, week_idx) → days used

    for t in prioritized:
        style = getattr(t, "scheduling_style", "balanced")
        if style != "deadline-loaded":
            continue
        rm = task_remaining.get(t.id, 0)
        if rm <= 0:
            continue
        deadline_dt = _as_vn_aware(t.deadline)
        days_until_dl = max(2, _days_until(deadline_dt, now))
        half_days = max(1, days_until_dl // 2)
        midpoint_str = (now + timedelta(days=half_days)).strftime("%Y-%m-%d")

        first_min = round(rm * 0.30)
        second_min = rm - first_min

        num_weeks_1 = max(1, (half_days + 6) // 7)
        slots_1 = num_weeks_1 * 3
        raw_q1 = max(MIN_SESSION_MINUTES, (first_min + slots_1 - 1) // slots_1)
        q1 = ((raw_q1 + 9) // 10) * 10

        second_days = days_until_dl - half_days
        num_weeks_2 = max(1, (second_days + 6) // 7)
        slots_2 = num_weeks_2 * 3
        raw_q2 = max(MIN_SESSION_MINUTES, (second_min + slots_2 - 1) // slots_2)
        q2 = ((raw_q2 + 9) // 10) * 10

        deadline_loaded_quota[t.id] = {"midpoint": midpoint_str, "q1": q1, "q2": q2}

    def _emit_session(task: TaskSchema, attempt: dict, milestone_title: Optional[str] = None) -> None:
        mins = attempt["minutes"]
        buf = round(mins * settings.buffer_percent)
        # C4: study_minutes = study time; occupied_minutes = study + buffer
        sessions.append(
            SessionSchema(
                id=str(uuid.uuid4()),
                taskId=task.id,
                source="task",
                sessionType="STUDY",
                subject=task.subject,
                title=task.title,
                plannedStart=attempt["session_start"].isoformat(),
                plannedEnd=attempt["session_end"].isoformat(),
                minutes=mins,
                studyMinutes=mins,
                occupiedMinutes=mins + buf,
                bufferMinutes=buf,
                status="pending",
                checklist=task_checklist[task.id],
                successCriteria=task_criteria[task.id],
                milestoneTitle=milestone_title,
                planVersion=plan_version,
            )
        )
        task_remaining[task.id] -= mins

    def _allocate_for_task(
        bucket: DayBucket,
        task: TaskSchema,
        minutes_needed: int,
        chunk_pref: int,
        allow_short: bool = False,
        milestone_title: Optional[str] = None,
    ) -> int:
        """Try to allocate minutes_needed from bucket for task. Returns minutes actually consumed."""
        consumed = 0
        local_remaining = minutes_needed
        attempt = _take_from_bucket(bucket, local_remaining, chunk_pref, allow_shorter_than_min=allow_short or bool(milestone_title))
        while attempt and local_remaining > 0:
            mins = attempt["minutes"]
            _emit_session(task, attempt, milestone_title)
            consumed += mins
            local_remaining -= mins
            attempt = (
                _take_from_bucket(bucket, local_remaining, chunk_pref, allow_shorter_than_min=allow_short or bool(milestone_title))
                if local_remaining > 0
                else None
            )
        return consumed

    # ── Main pass: per-bucket chronological, tasks sorted by urgency×style ──
    sorted_buckets = sorted(buckets, key=lambda b: b.iso_date)

    for bucket in sorted_buckets:
        bucket_dt = datetime.fromisoformat(f"{bucket.iso_date}T00:00:00+07:00")

        # Eligible tasks for this bucket: deadline >= bucket.date AND still has remaining
        eligible = [
            t for t in prioritized
            if task_remaining.get(t.id, 0) > 0
            and _as_vn_aware(t.deadline).strftime("%Y-%m-%d") >= bucket.iso_date
        ]
        if not eligible:
            continue

        # Sort by bucket-specific priority: urgency_score × style_weight (descending)
        eligible.sort(
            key=lambda t: _bucket_task_priority(t, bucket, now, task_remaining[t.id]),
            reverse=True,
        )

        for task in eligible:
            if bucket.used >= bucket.allowed_minutes:
                break
            rm = task_remaining[task.id]
            if rm <= 0:
                continue

            style = getattr(task, "scheduling_style", "balanced")
            is_balanced = style == "balanced" and task.id in balanced_quota
            is_dl = style == "deadline-loaded" and task.id in deadline_loaded_quota

            if is_balanced or is_dl:
                # Resolve quota and usage tracker
                week_idx = (bucket_dt.date() - now.date()).days // 7
                if is_balanced:
                    usage_dict = balanced_week_usage
                    quota = balanced_quota[task.id]
                else:
                    usage_dict = deadline_week_usage
                    dl_info = deadline_loaded_quota[task.id]
                    quota = dl_info["q1"] if bucket.iso_date <= dl_info["midpoint"] else dl_info["q2"]
                days_used = usage_dict.get((task.id, week_idx), 0)
                if days_used >= 3:
                    continue  # max 3 study-days per week
                total_consumed = 0
                if task.milestones:
                    remaining_quota = quota
                    for milestone in task.milestones:
                        if remaining_quota <= 0 or rm <= 0:
                            break
                        ms_needed = min(milestone.minutes_estimate, rm, remaining_quota)
                        consumed = _allocate_for_task(bucket, task, ms_needed, milestone.minutes_estimate, allow_short=True, milestone_title=milestone.title)
                        remaining_quota -= consumed
                        total_consumed += consumed
                        rm = task_remaining[task.id]
                else:
                    total_consumed = _allocate_for_task(bucket, task, min(quota, rm), focus_chunk)
                if total_consumed > 0:
                    usage_dict[(task.id, week_idx)] = days_used + 1
            else:
                if task.milestones:
                    for milestone in task.milestones:
                        ms_needed = min(milestone.minutes_estimate, rm)
                        _allocate_for_task(bucket, task, ms_needed, milestone.minutes_estimate, allow_short=True, milestone_title=milestone.title)
                        rm = task_remaining[task.id]
                        if rm <= 0:
                            break
                else:
                    _allocate_for_task(bucket, task, rm, focus_chunk)

    # ── Urgent enforcement: days_left ≤ URGENT_DAYS_THRESHOLD → ensure ≥ 1 session/day ──
    # If a task is urgent but got 0 sessions on an eligible day, force a short session (C4 Rule1).
    sessions_by_day_task: dict[tuple, int] = {}  # (iso_date, task_id) → session count
    for s in sessions:
        if s.source != "task" or not s.task_id:
            continue
        key = (s.planned_start[:10], s.task_id)
        sessions_by_day_task[key] = sessions_by_day_task.get(key, 0) + 1

    for task in prioritized:
        if task_remaining.get(task.id, 0) <= 0:
            continue
        deadline_dt = _as_vn_aware(task.deadline)
        days_left = _days_until(deadline_dt, now)
        if days_left > URGENT_DAYS_THRESHOLD:
            continue
        # Urgent task: ensure at least 1 session per remaining eligible bucket
        for bucket in sorted_buckets:
            bucket_dt = datetime.fromisoformat(f"{bucket.iso_date}T00:00:00+07:00")
            if bucket_dt < now:
                continue
            if bucket.iso_date > deadline_dt.strftime("%Y-%m-%d"):
                break
            if (bucket.iso_date, task.id) in sessions_by_day_task:
                continue  # already has a session on this day
            rm = task_remaining[task.id]
            if rm <= 0:
                break
            consumed = _allocate_for_task(bucket, task, rm, MIN_SESSION_MINUTES, allow_short=True)
            if consumed > 0:
                sessions_by_day_task[(bucket.iso_date, task.id)] = 1

    # ── EDF Fallback: fill empty bucket capacity with remaining tasks (C5 / B4) ──
    # Any bucket that still has capacity and there are still remaining tasks → fill them (EDF order).
    for bucket in sorted_buckets:
        if bucket.used >= bucket.allowed_minutes:
            continue
        leftover = [
            t for t in prioritized
            if task_remaining.get(t.id, 0) > 0
            and _as_vn_aware(t.deadline).strftime("%Y-%m-%d") >= bucket.iso_date
        ]
        if not leftover:
            continue
        # EDF: earliest deadline first
        leftover.sort(key=lambda t: _as_vn_aware(t.deadline).timestamp())
        edf_bucket_dt = datetime.fromisoformat(f"{bucket.iso_date}T00:00:00+07:00")
        for task in leftover:
            if bucket.used >= bucket.allowed_minutes:
                break
            rm = task_remaining[task.id]
            if rm <= 0:
                continue
            style = getattr(task, "scheduling_style", "balanced")
            is_balanced = style == "balanced" and task.id in balanced_quota
            is_dl = style == "deadline-loaded" and task.id in deadline_loaded_quota
            if is_balanced or is_dl:
                week_idx = (edf_bucket_dt.date() - now.date()).days // 7
                if is_balanced:
                    usage_dict = balanced_week_usage
                    quota = balanced_quota[task.id]
                else:
                    usage_dict = deadline_week_usage
                    dl_info = deadline_loaded_quota[task.id]
                    quota = dl_info["q1"] if bucket.iso_date <= dl_info["midpoint"] else dl_info["q2"]
                days_used = usage_dict.get((task.id, week_idx), 0)
                if days_used >= 3:
                    continue  # max 3 study-days per week
                total_consumed = 0
                if task.milestones:
                    remaining_quota = quota
                    for milestone in task.milestones:
                        if remaining_quota <= 0 or rm <= 0:
                            break
                        ms_needed = min(milestone.minutes_estimate, rm, remaining_quota)
                        consumed = _allocate_for_task(bucket, task, ms_needed, milestone.minutes_estimate, allow_short=True, milestone_title=milestone.title)
                        remaining_quota -= consumed
                        total_consumed += consumed
                        rm = task_remaining[task.id]
                else:
                    total_consumed = _allocate_for_task(bucket, task, min(quota, rm), focus_chunk)
                if total_consumed > 0:
                    usage_dict[(task.id, week_idx)] = days_used + 1
            else:
                if task.milestones:
                    for milestone in task.milestones:
                        ms_needed = min(milestone.minutes_estimate, rm)
                        _allocate_for_task(bucket, task, ms_needed, milestone.minutes_estimate, allow_short=True, milestone_title=milestone.title)
                        rm = task_remaining[task.id]
                        if rm <= 0:
                            break
                else:
                    _allocate_for_task(bucket, task, rm, focus_chunk)

    # ── Report unscheduled tasks ──────────────────────────────────────────
    for task in prioritized:
        rm = task_remaining.get(task.id, 0)
        effective_total = _effective_minutes(task)
        original_rm = max(0, effective_total - task.progress_minutes)
        scheduled_minutes = original_rm - rm
        if rm > 0:
            if scheduled_minutes == 0:
                unscheduled.append(task)
                suggestions.append(
                    PlanSuggestionSchema(
                        type="increase_free_time",
                        message=f'Nhiệm vụ "{task.title}" ({task.estimated_minutes}p) chưa được xếp lịch. Thêm slot hoặc lùi deadline.',
                    )
                )
            else:
                suggestions.append(
                    PlanSuggestionSchema(
                        type="reduce_duration",
                        message=(
                            f'Nhiệm vụ "{task.title}" chỉ xếp được {scheduled_minutes}/{task.estimated_minutes} phút '
                            f'(thiếu {rm}p). Thêm slot rảnh hoặc giảm ước lượng.'
                        ),
                    )
                )

    sessions_with_breaks = _apply_breaks(sessions, settings, plan_version)
    generated_at = datetime.utcnow().isoformat()

    # ------------------------------------------------------------------
    # Deduplicate suggestions
    # ------------------------------------------------------------------
    # Group per-day habit failures into a single summary line
    habit_fail_counts: dict[str, int] = {}
    other_suggestions: list[PlanSuggestionSchema] = []
    for s in suggestions:
        m = re.match(r'Không đủ slot cho habit "(.+)" vào .+\.', s.message)
        if m:
            habit_name = m.group(1)
            habit_fail_counts[habit_name] = habit_fail_counts.get(habit_name, 0) + 1
        else:
            other_suggestions.append(s)

    seen_msgs: set[str] = set()
    deduped: list[PlanSuggestionSchema] = []
    for s in other_suggestions:
        if s.message not in seen_msgs:
            seen_msgs.add(s.message)
            deduped.append(s)
    for habit_name, count in habit_fail_counts.items():
        deduped.append(
            PlanSuggestionSchema(
                type="increase_free_time",
                message=f'Habit "{habit_name}" không có slot trong {count} ngày. Hãy thêm thời gian rảnh.',
            )
        )
    suggestions = deduped

    return PlanRecordSchema(
        id=str(uuid.uuid4()),
        planVersion=plan_version,
        sessions=sessions_with_breaks,
        unscheduledTasks=[t.model_dump(by_alias=True) for t in unscheduled],
        suggestions=suggestions,
        generatedAt=generated_at,
    )
