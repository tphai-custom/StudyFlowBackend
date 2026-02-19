"""
ICS export for plan sessions.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any


def _to_ics_dt(iso_str: str) -> str:
    """Convert ISO datetime string to ICS YYYYMMDDTHHMMSSZ format."""
    iso_str = iso_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso_str)
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.strftime("%Y%m%dT%H%M%SZ")
    except Exception:
        # Fallback: strip non-UTC offset characters
        clean = iso_str[:19].replace("-", "").replace(":", "").replace("T", "T")
        return clean + "Z"


def generate_ics(sessions: List[Dict[str, Any]], generated_at: str) -> str:
    dtstamp = _to_ics_dt(generated_at)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//StudyFlow//Planner 1.0//VI",
        "CALSCALE:GREGORIAN",
    ]

    for s in sessions:
        if s.get("source") == "break":
            continue
        criteria = s.get("successCriteria") or []
        description = " \u2022 ".join(criteria) if criteria else ""
        lines += [
            "BEGIN:VEVENT",
            f"UID:{s['id']}@studyflow",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{_to_ics_dt(s['plannedStart'])}",
            f"DTEND:{_to_ics_dt(s['plannedEnd'])}",
            f"SUMMARY:{s['subject']} \u00b7 {s['title']}",
            f"DESCRIPTION:{description}",
            f"CATEGORIES:{s['subject']}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
