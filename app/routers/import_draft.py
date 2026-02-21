from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import import_draft as crud
from app.crud import tasks as tasks_crud
from app.database import get_db
from app.schemas.import_draft import ImportDraftCreate, ImportDraftSchema, ImportDraftUpdate
from app.schemas.task import TaskCreate

router = APIRouter(prefix="/imports", tags=["imports"])


def _to_schema(draft) -> ImportDraftSchema:
    return ImportDraftSchema(
        id=draft.id,
        draft_type=draft.draft_type,
        source_id=draft.source_id,
        name=draft.name,
        description=draft.description,
        items=draft.items or [],
        status=draft.status,
        created_at=draft.created_at.isoformat() if draft.created_at else "",
        updated_at=draft.updated_at.isoformat() if draft.updated_at else "",
    )


@router.get("/drafts")
async def list_drafts(
    type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    drafts = await crud.list_drafts(db, draft_type=type)
    return [_to_schema(d).model_dump(by_alias=False) for d in drafts]


@router.post("/drafts", status_code=status.HTTP_201_CREATED)
async def create_draft(payload: ImportDraftCreate, db: AsyncSession = Depends(get_db)):
    draft = await crud.create_draft(db, payload)
    return _to_schema(draft).model_dump(by_alias=False)


@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    draft = await crud.get_draft(db, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return _to_schema(draft).model_dump(by_alias=False)


@router.patch("/drafts/{draft_id}")
async def update_draft(draft_id: str, payload: ImportDraftUpdate, db: AsyncSession = Depends(get_db)):
    draft = await crud.update_draft(db, draft_id, payload)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return _to_schema(draft).model_dump(by_alias=False)


@router.post("/drafts/{draft_id}/finalize", status_code=status.HTTP_201_CREATED)
async def finalize_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    """Convert all draft items into real tasks."""
    draft = await crud.get_draft(db, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status == "finalized":
        raise HTTPException(status_code=400, detail="Draft already finalized")

    created_tasks = []
    for item in (draft.items or []):
        import datetime as dt_mod
        deadline_dt = dt_mod.datetime.utcnow() + dt_mod.timedelta(days=14)
        duration_min = item.get("durationMin", 30)
        task_payload = TaskCreate.model_validate({
            "subject": item.get("subject") or draft.name,
            "title": item.get("title", "Nhiệm vụ từ draft"),
            "deadline": deadline_dt.isoformat(),
            "timezone": "Asia/Ho_Chi_Minh",
            "difficulty": item.get("difficulty", 3),
            "durationEstimateMin": duration_min,
            "durationEstimateMax": duration_min,
            "durationUnit": "minutes",
            "estimatedMinutes": duration_min,
            "importance": 2,
            "contentFocus": item.get("notes") or "",
            "successCriteria": [item.get("successCriteria") or "Hoàn thành mục tiêu"],
            "milestones": None,
            "notes": item.get("notes") or "",
        })
        task = await tasks_crud.create_task(db, task_payload)
        created_tasks.append(str(task.id))

    await crud.finalize_draft(db, draft_id)
    return {"ok": True, "createdTaskIds": created_tasks, "count": len(created_tasks)}


@router.delete("/drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_draft(db, draft_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Draft not found")
