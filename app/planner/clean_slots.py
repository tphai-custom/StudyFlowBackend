"""
Utilities for cleaning and normalising free slots.
"""
from typing import List, Dict, Any


def _time_to_minutes(t: str) -> int:
    """Convert HH:MM string to minutes since midnight."""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _minutes_to_time(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def clean_slots(slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    For each weekday group:
    1. Sort slots by startTime
    2. Merge overlapping/adjacent slots
    3. Cap each merged slot at 180 minutes
    4. Recalculate capacityMinutes from start/end times
    """
    by_weekday: Dict[int, List[Dict[str, Any]]] = {}
    for s in slots:
        by_weekday.setdefault(s["weekday"], []).append(s)

    result: List[Dict[str, Any]] = []
    for weekday, day_slots in by_weekday.items():
        # Convert to (start_min, end_min, original_slot) tuples
        intervals = []
        for s in day_slots:
            start = _time_to_minutes(s["startTime"])
            end = _time_to_minutes(s["endTime"])
            if end > start:
                intervals.append((start, end, s))

        intervals.sort(key=lambda x: x[0])

        merged = []
        for start, end, src in intervals:
            if merged and start <= merged[-1][1]:
                # Overlapping — extend
                merged[-1] = (merged[-1][0], max(merged[-1][1], end), merged[-1][2])
            else:
                merged.append((start, end, src))

        for start, end, src in merged:
            duration = min(end - start, 180)
            capped_end = start + duration
            result.append({
                **src,
                "startTime": _minutes_to_time(start),
                "endTime": _minutes_to_time(capped_end),
                "capacityMinutes": duration,
            })

    return result
