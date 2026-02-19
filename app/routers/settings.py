import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SettingsModel

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_SETTINGS = {
    "dailyLimitMinutes": 240,
    "bufferPercent": 0.1,
    "breakPreset": {"focus": 45, "rest": 10, "label": "Deep work"},
    "timezone": "Asia/Ho_Chi_Minh",
}


class SettingsUpdate(BaseModel):
    dailyLimitMinutes: Optional[int] = None
    bufferPercent: Optional[float] = None
    breakPreset: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = None


def settings_to_dict(s: SettingsModel) -> dict:
    return {
        "id": s.id,
        "dailyLimitMinutes": s.dailyLimitMinutes,
        "bufferPercent": s.bufferPercent,
        "breakPreset": s.breakPreset,
        "timezone": s.timezone,
        "lastUpdated": s.lastUpdated,
    }


def get_or_create_settings(db: Session) -> SettingsModel:
    settings = db.query(SettingsModel).first()
    if not settings:
        now = datetime.utcnow().isoformat() + "Z"
        settings = SettingsModel(
            id=str(uuid.uuid4()),
            dailyLimitMinutes=DEFAULT_SETTINGS["dailyLimitMinutes"],
            bufferPercent=DEFAULT_SETTINGS["bufferPercent"],
            breakPreset=DEFAULT_SETTINGS["breakPreset"],
            timezone=DEFAULT_SETTINGS["timezone"],
            lastUpdated=now,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/")
def get_settings(db: Session = Depends(get_db)):
    return settings_to_dict(get_or_create_settings(db))


@router.put("/")
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    settings.lastUpdated = datetime.utcnow().isoformat() + "Z"
    db.commit()
    db.refresh(settings)
    return settings_to_dict(settings)
