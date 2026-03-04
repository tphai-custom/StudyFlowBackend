from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class LibraryItemCreate(BaseModel):
    subject: str
    grade: Optional[int] = None  # 6..10
    level: str
    title: str
    summary: str
    description: Optional[str] = None
    resource_type: str = "lesson"
    difficulty: Optional[int] = None  # 1..5
    url: Optional[str] = None
    tags: list[str] = []
    created_by: Optional[str] = None


class LibraryItemSchema(LibraryItemCreate):
    id: str

    model_config = {"from_attributes": True, "serialize_by_alias": True}


# ── v2 schemas ────────────────────────────────────────────────────────────────

class LibraryItemV2Schema(BaseModel):
    """One record per (grade, subject). Returned by GET /library."""
    id: str
    grade: int
    subject: str
    title: str
    lessons: list[str] = []
    summaries: list[str] = []
    exercises: list[str] = []
    videos: list[str] = []
    tags: list[str] = []

    model_config = {"from_attributes": True}


class LibrarySeedRequest(BaseModel):
    """Body for POST /admin/library/seed."""
    grades: list[int] = list(range(6, 11))   # default: all 6..10
    subjects: list[str] = ["toan", "ngu_van", "tieng_anh", "lich_su", "dia_li"]
    mode: str = "upsert"  # currently only "upsert" is supported


class LibrarySeedResponse(BaseModel):
    inserted_count: int
    updated_count: int
    skipped_count: int
