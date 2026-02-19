import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PlanModel, SessionModel, TaskModel, SlotModel, HabitModel, SettingsModel
from app.routers.settings import get_or_create_settings
from app.planner.generate_plan import generate_plan
from app.planner.ics_export import generate_ics

router = APIRouter(prefix="/plan", tags=["plan"])


def session_to_dict(s: SessionModel) -> dict:
    return {
        "id": s.id,
        "taskId": s.taskId,
        "habitId": s.habitId,
        "source": s.source,
        "subject": s.subject,
        "title": s.title,
        "plannedStart": s.plannedStart,
        "plannedEnd": s.plannedEnd,
        "minutes": s.minutes,
        "bufferMinutes": s.bufferMinutes,
        "status": s.status,
        "checklist": s.checklist,
        "successCriteria": s.successCriteria,
        "milestoneTitle": s.milestoneTitle,
        "completedAt": s.completedAt,
        "planVersion": s.planVersion,
    }


def task_to_dict(t: TaskModel) -> dict:
    return {
        "id": t.id,
        "subject": t.subject,
        "title": t.title,
        "deadline": t.deadline,
        "timezone": t.timezone,
        "difficulty": t.difficulty,
        "durationEstimateMin": t.durationEstimateMin,
        "durationEstimateMax": t.durationEstimateMax,
        "durationUnit": t.durationUnit,
        "estimatedMinutes": t.estimatedMinutes,
        "importance": t.importance,
        "contentFocus": t.contentFocus,
        "successCriteria": t.successCriteria or [],
        "milestones": t.milestones,
        "notes": t.notes,
        "createdAt": t.createdAt,
        "updatedAt": t.updatedAt,
        "progressMinutes": t.progressMinutes,
    }


@router.get("/latest")
def get_latest_plan(db: Session = Depends(get_db)):
    plan = db.query(PlanModel).order_by(PlanModel.planVersion.desc()).first()
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found")

    plan_sessions = (
        db.query(SessionModel)
        .filter(SessionModel.planVersion == plan.planVersion)
        .all()
    )
    return {
        "planVersion": plan.planVersion,
        "sessions": [session_to_dict(s) for s in plan_sessions],
        "unscheduledTasks": plan.unscheduledTasks or [],
        "suggestions": plan.suggestions or [],
        "generatedAt": plan.generatedAt,
    }


@router.post("/rebuild")
def rebuild_plan(db: Session = Depends(get_db)):
    tasks = db.query(TaskModel).all()
    slots = db.query(SlotModel).all()
    habits = db.query(HabitModel).all()
    settings = get_or_create_settings(db)

    tasks_data = [task_to_dict(t) for t in tasks]
    slots_data = [
        {
            "id": s.id,
            "weekday": s.weekday,
            "startTime": s.startTime,
            "endTime": s.endTime,
            "capacityMinutes": s.capacityMinutes,
            "source": s.source,
            "createdAt": s.createdAt,
        }
        for s in slots
    ]
    habits_data = [
        {
            "id": h.id,
            "name": h.name,
            "cadence": h.cadence,
            "weekday": h.weekday,
            "minutes": h.minutes,
            "preset": h.preset,
            "preferredStart": h.preferredStart,
            "energyWindow": h.energyWindow,
            "createdAt": h.createdAt,
        }
        for h in habits
    ]
    settings_data = {
        "dailyLimitMinutes": settings.dailyLimitMinutes,
        "bufferPercent": settings.bufferPercent,
        "breakPreset": settings.breakPreset,
        "timezone": settings.timezone,
    }

    # Get current plan version
    latest_plan = db.query(PlanModel).order_by(PlanModel.planVersion.desc()).first()
    current_version = latest_plan.planVersion if latest_plan else 0

    result = generate_plan(tasks_data, slots_data, habits_data, settings_data, current_version)

    # Delete old sessions for this new version (shouldn't be any, but just in case)
    db.query(SessionModel).filter(
        SessionModel.planVersion == result["planVersion"]
    ).delete()

    # Save new plan
    plan_record = PlanModel(
        id=str(uuid.uuid4()),
        planVersion=result["planVersion"],
        unscheduledTasks=result["unscheduledTasks"],
        suggestions=result["suggestions"],
        generatedAt=result["generatedAt"],
    )
    db.add(plan_record)

    # Save sessions
    for s in result["sessions"]:
        session_record = SessionModel(
            id=s["id"],
            taskId=s.get("taskId"),
            habitId=s.get("habitId"),
            source=s["source"],
            subject=s["subject"],
            title=s["title"],
            plannedStart=s["plannedStart"],
            plannedEnd=s["plannedEnd"],
            minutes=s["minutes"],
            bufferMinutes=s.get("bufferMinutes", 0),
            status=s.get("status", "pending"),
            checklist=s.get("checklist"),
            successCriteria=s.get("successCriteria"),
            milestoneTitle=s.get("milestoneTitle"),
            completedAt=s.get("completedAt"),
            planVersion=result["planVersion"],
        )
        db.add(session_record)

    db.commit()

    # Re-query to return fresh data
    saved_sessions = (
        db.query(SessionModel)
        .filter(SessionModel.planVersion == result["planVersion"])
        .all()
    )
    return {
        "planVersion": result["planVersion"],
        "sessions": [session_to_dict(s) for s in saved_sessions],
        "unscheduledTasks": result["unscheduledTasks"],
        "suggestions": result["suggestions"],
        "generatedAt": result["generatedAt"],
    }


@router.get("/export/ics")
def export_ics(db: Session = Depends(get_db)):
    plan = db.query(PlanModel).order_by(PlanModel.planVersion.desc()).first()
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found")

    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.planVersion == plan.planVersion)
        .all()
    )
    sessions_data = [session_to_dict(s) for s in sessions]
    ics_content = generate_ics(sessions_data, plan.generatedAt)

    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=studyflow.ics"},
    )


class SessionStatusUpdate(BaseModel):
    status: str


@router.patch("/sessions/{session_id}/status")
def update_session_status(
    session_id: str,
    body: SessionStatusUpdate,
    db: Session = Depends(get_db),
):
    if body.status not in ("pending", "done", "skipped"):
        raise HTTPException(status_code=422, detail="Invalid status value")

    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from datetime import datetime, timezone

    session.status = body.status
    if body.status == "done":
        session.completedAt = datetime.utcnow().isoformat() + "Z"
    elif body.status in ("pending", "skipped"):
        session.completedAt = None
    db.commit()
    db.refresh(session)
    return session_to_dict(session)
