from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, Field


class FreeSlotBase(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: str = Field(alias="startTime")  # HH:mm
    end_time: str = Field(alias="endTime")  # HH:mm
    capacity_minutes: int = Field(alias="capacityMinutes", ge=1)
    source: Optional[Literal["user", "auto"]] = "user"

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class FreeSlotCreate(FreeSlotBase):
    pass


class FreeSlotSchema(FreeSlotBase):
    id: str
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True, "from_attributes": True, "serialize_by_alias": True}
