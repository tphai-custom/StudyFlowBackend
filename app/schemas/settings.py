from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BreakPresetSchema(BaseModel):
    focus: int = 45
    rest: int = 10
    label: str = "Deep work 45/10"


class AppSettingsSchema(BaseModel):
    id: str = "app-settings"
    daily_limit_minutes: int = Field(alias="dailyLimitMinutes", default=180, ge=30, le=720)
    buffer_percent: float = Field(alias="bufferPercent", default=0.15, ge=0.0, le=0.5)
    break_preset: BreakPresetSchema = Field(
        alias="breakPreset",
        default_factory=lambda: BreakPresetSchema(),
    )
    timezone: str = "Asia/Ho_Chi_Minh"
    last_updated: datetime = Field(alias="lastUpdated", default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "from_attributes": True, "serialize_by_alias": True}
