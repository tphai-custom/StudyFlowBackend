"""Port of icsExport.ts — generate iCalendar (.ics) content from a plan."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.schemas.plan import PlanRecordSchema

CRLF = "\r\n"
PALETTE = ["#6EE7B7", "#93C5FD", "#FCD34D", "#FCA5A5", "#C4B5FD", "#F9A8D4"]


def _get_color(subject: str) -> str:
    index = abs(sum(ord(c) for c in subject)) % len(PALETTE)
    return PALETTE[index]


def _format_date(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y%m%dT%H%M%SZ")


def _get(session: Any, key: str, camel_key: str) -> Any:
    """Get a value from either a dict (camelCase) or a SessionSchema object."""
    if isinstance(session, dict):
        return session.get(camel_key) or session.get(key)
    return getattr(session, key, None) or getattr(session, camel_key, None)


def plan_to_ics(plan: PlanRecordSchema) -> str:
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//StudyFlow//Planner 1.0//VI",
        "CALSCALE:GREGORIAN",
    ]

    for session in plan.sessions:
        source = _get(session, "source", "source")
        if source == "break":
            continue
        session_id = _get(session, "id", "id")
        planned_start = _get(session, "planned_start", "plannedStart")
        planned_end = _get(session, "planned_end", "plannedEnd")
        subject = _get(session, "subject", "subject")
        title = _get(session, "title", "title")
        criteria = _get(session, "success_criteria", "successCriteria") or []
        description = " • ".join(criteria) if criteria else "Hoàn thành buổi học"

        lines += [
            "BEGIN:VEVENT",
            f"UID:{session_id}@studyflow",
            f"DTSTAMP:{_format_date(plan.generated_at)}",
            f"DTSTART:{_format_date(planned_start)}",
            f"DTEND:{_format_date(planned_end)}",
            f"SUMMARY:{subject} · {title}",
            f"DESCRIPTION:{description}",
            f"CATEGORIES:{subject}",
            f"COLOR:{_get_color(subject)}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return CRLF.join(lines)
