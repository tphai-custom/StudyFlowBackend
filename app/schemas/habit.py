from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, Field


class HabitBase(BaseModel):
    name: str
    cadence: Literal["daily", "weekly"]
    weekday: Optional[int] = Field(default=None, ge=0, le=6)
    minutes: int = Field(ge=1)
    preset: Optional[Literal["pomodoro", "deep-work", "focus-30"]] = None
    preferred_start: Optional[str] = Field(alias="preferredStart", default=None)
    energy_window: Optional[Literal["morning", "afternoon", "evening"]] = Field(
        alias="energyWindow", default=None
    )

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class HabitCreate(HabitBase):
    pass


class HabitSchema(HabitBase):
    id: str
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True, "from_attributes": True, "serialize_by_alias": True}
