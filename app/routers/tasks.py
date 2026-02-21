from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import tasks as crud
from app.crud import plan as plan_crud
from app.database import get_db
from app.schemas.task import TaskCreate, TaskSchema, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskSchema])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    rows = await crud.list_tasks(db)
    return rows


@router.post("/", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_task(db, payload)


@router.get("/{task_id}", response_model=TaskSchema)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskSchema)
async def update_task(task_id: str, payload: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await crud.update_task(db, task_id, payload)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    await plan_crud.remove_task_from_plans(db, task_id)


@router.patch("/{task_id}/progress", response_model=TaskSchema)
async def update_progress(task_id: str, progress_minutes: int, db: AsyncSession = Depends(get_db)):
    task = await crud.update_task_progress(db, task_id, progress_minutes)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ---------------------------------------------------------------------------
# Rule-based breakdown suggestions (no AI required)
# ---------------------------------------------------------------------------

_BREAKDOWN_TEMPLATES: dict[str, list[dict]] = {
    "Toán": [
        {"title": "Ôn công thức và lý thuyết", "durationPct": 0.15, "criteria": "Thuộc công thức chính"},
        {"title": "Làm bài tập cơ bản", "durationPct": 0.30, "criteria": "Giải đúng ≥8/10 bài cơ bản"},
        {"title": "Làm bài tập nâng cao", "durationPct": 0.30, "criteria": "Giải được 2/3 bài nâng cao"},
        {"title": "Chữa lỗi và ghi chú", "durationPct": 0.15, "criteria": "Ghi chép lỗi thường gặp"},
        {"title": "Tổng kết", "durationPct": 0.10, "criteria": "Tóm tắt kiến thức vừa học"},
    ],
    "Anh": [
        {"title": "Học từ vựng mới", "durationPct": 0.25, "criteria": "Ghi nhớ 10 từ mới"},
        {"title": "Nghe / Đọc hiểu", "durationPct": 0.30, "criteria": "Trả lời đúng 80% câu hỏi"},
        {"title": "Luyện viết / nói", "durationPct": 0.30, "criteria": "Viết được 1 đoạn văn"},
        {"title": "Kỳ thuật làm bài thi", "durationPct": 0.15, "criteria": "Nắm chiến lược làm bài"},
    ],
    "Văn": [
        {"title": "Đọc hiểu tác phẩm", "durationPct": 0.20, "criteria": "Nắm nội dung chính"},
        {"title": "Phân tích nhân vật / chủ đề", "durationPct": 0.35, "criteria": "Phân tích được nhân vật chính"},
        {"title": "Luyện viết đoạn văn", "durationPct": 0.30, "criteria": "Viết đoạn 200 chữ đúng cấu trúc"},
        {"title": "Soát lỗi + tổng kết", "durationPct": 0.15, "criteria": "Không còn lỗi viết tắt"},
    ],
    "Lý": [
        {"title": "Ôn lý thuyết + công thức", "durationPct": 0.20, "criteria": "Thuộc công thức cần thiết"},
        {"title": "Bài tập tự luận cơ bản", "durationPct": 0.35, "criteria": "Giải đúng 5 bài cơ bản"},
        {"title": "Bài tập nâng cao", "durationPct": 0.30, "criteria": "Giải 2 bài nâng cao"},
        {"title": "Chữa lỗi", "durationPct": 0.15, "criteria": "Hiểu nguyên nhân sai"},
    ],
}
_DEFAULT_TEMPLATE = [
    {"title": "Nhìn lại kiến thức cần luỳn", "durationPct": 0.20, "criteria": "Nắm vững yêu cầu"},
    {"title": "Thực hành chính", "durationPct": 0.50, "criteria": "Hoàn thành ít nhất 50% khối lượng"},
    {"title": "Kiểm tra lại + ghi chú", "durationPct": 0.20, "criteria": "Ghi chép những điểm cần nhớ"},
    {"title": "Tổng kết", "durationPct": 0.10, "criteria": "Tự giải thích lại cho người khác"},
]


@router.post("/{task_id}/suggest-breakdown")
async def suggest_breakdown(task_id: str, db: AsyncSession = Depends(get_db)):
    """Return rule-based subtasks + success criteria for a task."""
    task = await crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    template = _BREAKDOWN_TEMPLATES.get(task.subject, _DEFAULT_TEMPLATE)
    total_minutes = task.estimated_minutes

    subtasks = [
        {
            "title": step["title"],
            "minutesEstimate": max(5, round(total_minutes * step["durationPct"])),
            "successCriteria": step["criteria"],
        }
        for step in template
    ]
    return {
        "taskId": task_id,
        "subject": task.subject,
        "totalMinutes": total_minutes,
        "subtasks": subtasks,
        "suggestedSuccessCriteria": [step["criteria"] for step in template],
    }
