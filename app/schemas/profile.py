from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EnergyLevel = Literal["low", "medium", "high"]


class EnergyPreferences(BaseModel):
    morning: EnergyLevel = "medium"
    afternoon: EnergyLevel = "medium"
    evening: EnergyLevel = "medium"


class UserProfileSchema(BaseModel):
    id: str = "user-profile"
    grade_level: str = Field(alias="gradeLevel", default="Chưa thiết lập")
    goals: list[str] = Field(default_factory=list)
    weak_subjects: list[str] = Field(alias="weakSubjects", default_factory=list)
    strong_subjects: list[str] = Field(alias="strongSubjects", default_factory=list)
    learning_pace: Literal["slow", "balanced", "fast"] = Field(
        alias="learningPace", default="balanced"
    )
    energy_preferences: EnergyPreferences = Field(
        alias="energyPreferences", default_factory=EnergyPreferences
    )
    daily_limit_preference: int = Field(alias="dailyLimitPreference", default=180)
    favorite_break_preset: str = Field(alias="favoriteBreakPreset", default="Pomodoro 50/10")
    timezone: str = "Asia/Ho_Chi_Minh"
    updated_at: datetime = Field(alias="updatedAt", default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "from_attributes": True, "serialize_by_alias": True}


class UserProfileUpdate(BaseModel):
    grade_level: str = Field(alias="gradeLevel")
    goals: list[str] = Field(default_factory=list)
    weak_subjects: list[str] = Field(alias="weakSubjects", default_factory=list)
    strong_subjects: list[str] = Field(alias="strongSubjects", default_factory=list)
    learning_pace: Literal["slow", "balanced", "fast"] = Field(
        alias="learningPace", default="balanced"
    )
    energy_preferences: EnergyPreferences = Field(
        alias="energyPreferences", default_factory=EnergyPreferences
    )
    daily_limit_preference: int = Field(alias="dailyLimitPreference", default=180)
    favorite_break_preset: str = Field(alias="favoriteBreakPreset", default="Pomodoro 50/10")
    timezone: str = "Asia/Ho_Chi_Minh"

    model_config = {"populate_by_name": True}
