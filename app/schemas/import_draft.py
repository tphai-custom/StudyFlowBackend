from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class DraftItemSchema(BaseModel):
    id: str
    title: str
    durationMin: int = Field(default=30)
    difficulty: int = Field(default=3, ge=1, le=5)
    subject: str = Field(default="")
    successCriteria: str = Field(default="Hoàn thành mục tiêu")
    orderIndex: int = Field(default=0)
    notes: str = Field(default="")

    model_config = {"populate_by_name": True}


class ImportDraftSchema(BaseModel):
    id: str
    draftType: str = Field(alias="draft_type")
    sourceId: str = Field(alias="source_id")
    name: str
    description: str
    items: List[DraftItemSchema]
    status: Literal["draft", "finalized"]
    createdAt: str = Field(alias="created_at")
    updatedAt: str = Field(alias="updated_at")

    model_config = {"populate_by_name": True, "from_attributes": True}


class ImportDraftCreate(BaseModel):
    draftType: Literal["template", "program"]
    sourceId: str
    name: str
    description: str = ""
    items: List[DraftItemSchema] = Field(default_factory=list)


class ImportDraftUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[DraftItemSchema]] = None
