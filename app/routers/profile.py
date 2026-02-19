import uuid
from datetime import datetime
from typing import Optional, List, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProfileModel

router = APIRouter(prefix="/profile", tags=["profile"])

DEFAULT_PROFILE = {
    "gradeLevel": "Lớp 10",
    "goals": [],
    "weakSubjects": [],
    "strongSubjects": [],
    "learningPace": "balanced",
    "energyPreferences": {"morning": "medium", "afternoon": "medium", "evening": "high"},
    "dailyLimitPreference": 120,
    "favoriteBreakPreset": "deep-work",
    "timezone": "Asia/Ho_Chi_Minh",
}


class ProfileUpdate(BaseModel):
    gradeLevel: Optional[str] = None
    goals: Optional[List[str]] = None
    weakSubjects: Optional[List[str]] = None
    strongSubjects: Optional[List[str]] = None
    learningPace: Optional[str] = None
    energyPreferences: Optional[Dict[str, str]] = None
    dailyLimitPreference: Optional[int] = None
    favoriteBreakPreset: Optional[str] = None
    timezone: Optional[str] = None


def profile_to_dict(p: ProfileModel) -> dict:
    return {
        "id": p.id,
        "gradeLevel": p.gradeLevel,
        "goals": p.goals or [],
        "weakSubjects": p.weakSubjects or [],
        "strongSubjects": p.strongSubjects or [],
        "learningPace": p.learningPace,
        "energyPreferences": p.energyPreferences,
        "dailyLimitPreference": p.dailyLimitPreference,
        "favoriteBreakPreset": p.favoriteBreakPreset,
        "timezone": p.timezone,
        "updatedAt": p.updatedAt,
    }


def get_or_create_profile(db: Session) -> ProfileModel:
    p = db.query(ProfileModel).first()
    if not p:
        now = datetime.utcnow().isoformat() + "Z"
        p = ProfileModel(
            id=str(uuid.uuid4()),
            gradeLevel=DEFAULT_PROFILE["gradeLevel"],
            goals=DEFAULT_PROFILE["goals"],
            weakSubjects=DEFAULT_PROFILE["weakSubjects"],
            strongSubjects=DEFAULT_PROFILE["strongSubjects"],
            learningPace=DEFAULT_PROFILE["learningPace"],
            energyPreferences=DEFAULT_PROFILE["energyPreferences"],
            dailyLimitPreference=DEFAULT_PROFILE["dailyLimitPreference"],
            favoriteBreakPreset=DEFAULT_PROFILE["favoriteBreakPreset"],
            timezone=DEFAULT_PROFILE["timezone"],
            updatedAt=now,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


@router.get("/")
def get_profile(db: Session = Depends(get_db)):
    return profile_to_dict(get_or_create_profile(db))


@router.put("/")
def update_profile(body: ProfileUpdate, db: Session = Depends(get_db)):
    p = get_or_create_profile(db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    p.updatedAt = datetime.utcnow().isoformat() + "Z"
    db.commit()
    db.refresh(p)
    return profile_to_dict(p)
