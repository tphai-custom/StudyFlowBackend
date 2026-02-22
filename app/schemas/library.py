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
