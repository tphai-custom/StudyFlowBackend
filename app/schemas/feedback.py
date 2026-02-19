from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    label: Literal["too_dense", "too_easy", "need_more_time", "evening_focus", "custom"]
    note: Optional[str] = None
    plan_version: int = Field(alias="planVersion")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class FeedbackSchema(FeedbackCreate):
    id: str
    submitted_at: datetime = Field(alias="submittedAt")

    model_config = {"populate_by_name": True, "from_attributes": True, "serialize_by_alias": True}
