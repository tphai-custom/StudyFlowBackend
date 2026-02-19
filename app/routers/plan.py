from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import plan as plan_crud
from app.database import get_db
from app.planner.ics_export import plan_to_ics
from app.planner.plan_service import rebuild_plan
from app.schemas.plan import PlanRecordSchema, SessionStatusUpdate

router = APIRouter(prefix="/plan", tags=["plan"])


def _row_to_schema(plan) -> PlanRecordSchema:
    return PlanRecordSchema(
        id=plan.id,
        planVersion=plan.plan_version,
        sessions=plan.sessions,
        unscheduledTasks=plan.unscheduled_tasks,
        suggestions=plan.suggestions,
        generatedAt=plan.generated_at,
    )


@router.get("/latest")
async def get_latest_plan(db: AsyncSession = Depends(get_db)):
    plan = await plan_crud.get_latest_plan(db)
    if plan is None:
        raise HTTPException(status_code=404, detail="No plan found")
    return _row_to_schema(plan).model_dump(by_alias=True)


@router.post("/rebuild")
async def rebuild(db: AsyncSession = Depends(get_db)):
    plan = await rebuild_plan(db)
    if plan is None:
        raise HTTPException(
            status_code=400,
            detail="Cần ít nhất 1 task và 1 free slot để tạo kế hoạch.",
        )
    return plan.model_dump(by_alias=True)


@router.patch("/sessions/{session_id}/status", response_model=dict)
async def update_session_status(
    session_id: str,
    payload: SessionStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    plan = await plan_crud.update_session_status(db, session_id, payload.status)
    if plan is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@router.get("/export/ics")
async def export_ics(db: AsyncSession = Depends(get_db)):
    plan_row = await plan_crud.get_latest_plan(db)
    if plan_row is None:
        raise HTTPException(status_code=404, detail="No plan found")
    plan = _row_to_schema(plan_row)
    ics_content = plan_to_ics(plan)
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="studyflow.ics"'},
    )

