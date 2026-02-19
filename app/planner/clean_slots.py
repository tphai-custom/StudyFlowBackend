"""Port of cleanSlots.ts — sanitise and merge overlapping FreeSlot records."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from app.schemas.free_slot import FreeSlotSchema


class CleanSlotsResult(TypedDict):
    slots: list[FreeSlotSchema]
    warnings: list[str]


def _to_minutes(time: str) -> int:
    h, m = map(int, time.split(":"))
    return h * 60 + m


def _from_minutes(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def clean_slots(slots: list[FreeSlotSchema]) -> CleanSlotsResult:
    warnings: list[str] = []
    grouped: dict[int, list[FreeSlotSchema]] = {}

    for slot in slots:
        start = _to_minutes(slot.start_time)
        end = _to_minutes(slot.end_time)
        if end <= start:
            warnings.append(f"Slot {slot.start_time}-{slot.end_time} bị đảo giờ.")
            continue
        duration = end - start
        if duration >= 720:
            warnings.append(
                f"Slot {slot.start_time}-{slot.end_time} quá dài, đã giới hạn 180 phút."
            )
        safe_duration = min(duration, 180)
        safe_end = _from_minutes(start + safe_duration)
        clean = FreeSlotSchema(
            **{
                **slot.model_dump(by_alias=False),
                "start_time": _from_minutes(start),
                "end_time": safe_end,
                "capacity_minutes": safe_duration,
            }
        )
        grouped.setdefault(slot.weekday, []).append(clean)

    sanitized: list[FreeSlotSchema] = []
    for weekday, day_slots in grouped.items():
        sorted_slots = sorted(day_slots, key=lambda s: _to_minutes(s.start_time))
        current = sorted_slots[0]
        before_count = len(sorted_slots)
        for s in sorted_slots[1:]:
            if _to_minutes(s.start_time) <= _to_minutes(current.end_time):
                merged_start = _to_minutes(current.start_time)
                merged_end = max(_to_minutes(s.end_time), _to_minutes(current.end_time))
                current = FreeSlotSchema(
                    **{
                        **current.model_dump(by_alias=False),
                        "start_time": _from_minutes(merged_start),
                        "end_time": _from_minutes(merged_end),
                        "capacity_minutes": merged_end - merged_start,
                    }
                )
            else:
                sanitized.append(current)
                current = s
        sanitized.append(current)
        after_count = sum(1 for sl in sanitized if sl.weekday == weekday)
        if after_count < before_count:
            warnings.append(f"Đã gộp slot trùng trong ngày {weekday}")

    return {"slots": sanitized, "warnings": warnings}
