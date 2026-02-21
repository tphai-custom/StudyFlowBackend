"""Schemas for parent–student linking and suggestions."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class LinkRequest(BaseModel):
    """Sent by a parent to link with a student using the student's link_code."""
    child_username: str
    link_code: str


class LinkSchema(BaseModel):
    id: str
    parent_id: str
    student_id: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LinkStatusUpdate(BaseModel):
    status: str  # active | rejected


class SuggestionCreate(BaseModel):
    type: str
    payload: dict[str, Any] = {}
    message: Optional[str] = None


class SuggestionSchema(BaseModel):
    id: str
    parent_id: str
    student_id: str
    type: str
    payload: dict[str, Any] = {}
    message: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SuggestionStatusUpdate(BaseModel):
    status: str  # accepted | rejected
