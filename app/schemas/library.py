from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class LibraryItemCreate(BaseModel):
    subject: str
    level: str
    title: str
    summary: str
    url: Optional[str] = None
    tags: list[str] = []


class LibraryItemSchema(LibraryItemCreate):
    id: str

    model_config = {"from_attributes": True, "serialize_by_alias": True}
