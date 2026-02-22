from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class PlanOverrideCreate(BaseModel):
    plan_id: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    payload: list[Any] = Field(default_factory=list)  # list of session overrides


class PlanOverrideSchema(PlanOverrideCreate):
    id: str
    user_id: str
    edited_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
