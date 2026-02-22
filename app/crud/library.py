from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import LibraryItem
from app.schemas.library import LibraryItemCreate

# ---------------------------------------------------------------------------
# Seed data: 5 subjects × grades 6-10 × 2-3 items each ≈ 65 items
# ---------------------------------------------------------------------------
_SEED_DATA: list[dict] = []

_SUBJECTS_CONTENT = {
    "toan": {
        "items_per_grade": [
            {"title": "Lý thuyết Toán lớp {}", "summary": "Tóm tắt lý thuyết Toán lớp {} – công thức cơ bản và bài tập mẫu.", "resource_type": "summary", "difficulty": 2, "tags": ["lý thuyết", "công thức"]},
            {"title": "Bài tập Đại số lớp {}", "summary": "Bộ bài tập đại số lớp {} có đáp án chi tiết.", "resource_type": "worksheet", "difficulty": 3, "tags": ["bài tập", "đại số"]},
            {"title": "Video giải đề Toán lớp {}", "summary": "Video hướng dẫn giải các dạng bài thi Toán lớp {} phổ biến.", "resource_type": "video", "difficulty": 3, "tags": ["video", "giải đề"]},
        ],
    },
    "ngu_van": {
        "items_per_grade": [
            {"title": "Tóm tắt tác phẩm Văn lớp {}", "summary": "Tóm tắt các tác phẩm văn học trong chương trình Ngữ văn lớp {}.", "resource_type": "summary", "difficulty": 2, "tags": ["tóm tắt", "văn học"]},
            {"title": "Phân tích văn bản Văn lớp {}", "summary": "Hướng dẫn phân tích các văn bản trọng tâm Ngữ văn lớp {}.", "resource_type": "lesson", "difficulty": 3, "tags": ["phân tích", "văn bản"]},
            {"title": "Đề cương ôn tập Văn lớp {}", "summary": "Đề cương hệ thống kiến thức Ngữ văn lớp {} theo chủ đề.", "resource_type": "summary", "difficulty": 2, "tags": ["ôn tập", "đề cương"]},
        ],
    },
    "tieng_anh": {
        "items_per_grade": [
            {"title": "Từ vựng Tiếng Anh lớp {}", "summary": "Danh sách từ vựng trọng tâm chương trình Tiếng Anh lớp {}.", "resource_type": "lesson", "difficulty": 2, "tags": ["từ vựng", "unit"]},
            {"title": "Ngữ pháp Tiếng Anh lớp {}", "summary": "Tổng hợp ngữ pháp Tiếng Anh lớp {} với ví dụ và bài tập.", "resource_type": "summary", "difficulty": 3, "tags": ["ngữ pháp", "grammar"]},
            {"title": "Bài tập Reading lớp {}", "summary": "Bộ bài đọc hiểu Tiếng Anh lớp {} kèm đáp án.", "resource_type": "worksheet", "difficulty": 3, "tags": ["reading", "bài tập"]},
        ],
    },
    "lich_su": {
        "items_per_grade": [
            {"title": "Niên biểu Lịch sử lớp {}", "summary": "Niên biểu các sự kiện, nhân vật lịch sử quan trọng trong chương trình lớp {}.", "resource_type": "summary", "difficulty": 2, "tags": ["niên biểu", "sự kiện"]},
            {"title": "Bài tập ôn tập Lịch sử lớp {}", "summary": "Bộ câu hỏi ôn tập Lịch sử lớp {} theo dạng trắc nghiệm và tự luận.", "resource_type": "worksheet", "difficulty": 2, "tags": ["ôn tập", "trắc nghiệm"]},
        ],
    },
    "dia_li": {
        "items_per_grade": [
            {"title": "Bản đồ & lược đồ Địa lí lớp {}", "summary": "Hướng dẫn đọc bản đồ và lược đồ địa lí lớp {} kèm câu hỏi thực hành.", "resource_type": "lesson", "difficulty": 2, "tags": ["bản đồ", "lược đồ"]},
            {"title": "Tóm tắt Địa lí lớp {}", "summary": "Tóm tắt kiến thức Địa lí lớp {} theo từng chương, dễ ôn tập.", "resource_type": "summary", "difficulty": 2, "tags": ["tóm tắt", "ôn tập"]},
        ],
    },
}

for _subject, _config in _SUBJECTS_CONTENT.items():
    for _grade in range(6, 11):
        for _tmpl in _config["items_per_grade"]:
            _SEED_DATA.append({
                "subject": _subject,
                "grade": _grade,
                "level": f"Lớp {_grade}",
                "title": _tmpl["title"].format(_grade),
                "summary": _tmpl["summary"].format(_grade),
                "description": _tmpl["summary"].format(_grade),
                "resource_type": _tmpl["resource_type"],
                "difficulty": _tmpl["difficulty"],
                "url": None,
                "tags": _tmpl["tags"],
                "owner_user_id": None,
                "created_by": "system",
            })


# ---------------------------------------------------------------------------
# CRUD functions
# ---------------------------------------------------------------------------

async def list_library(db: AsyncSession, owner_user_id: str) -> list[LibraryItem]:
    """Return system-shared items + user's own items."""
    result = await db.execute(
        select(LibraryItem)
        .where(or_(LibraryItem.owner_user_id.is_(None), LibraryItem.owner_user_id == owner_user_id))
        .order_by(LibraryItem.subject, LibraryItem.grade, LibraryItem.title)
    )
    return list(result.scalars().all())


async def search_library(
    db: AsyncSession,
    owner_user_id: str,
    query: Optional[str] = None,
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    resource_type: Optional[str] = None,
) -> list[LibraryItem]:
    conditions = [or_(LibraryItem.owner_user_id.is_(None), LibraryItem.owner_user_id == owner_user_id)]
    if subject:
        conditions.append(LibraryItem.subject == subject)
    if grade:
        conditions.append(LibraryItem.grade == grade)
    if resource_type:
        conditions.append(LibraryItem.resource_type == resource_type)

    stmt = (
        select(LibraryItem)
        .where(and_(*conditions))
        .order_by(LibraryItem.subject, LibraryItem.grade, LibraryItem.title)
    )
    items = list((await db.execute(stmt)).scalars().all())

    if query:
        q = query.lower()
        items = [
            item for item in items
            if q in f"{item.title} {item.summary} {' '.join(item.tags)}".lower()
        ]
    return items


async def save_library_items(
    db: AsyncSession,
    items: list[LibraryItemCreate],
    owner_user_id: Optional[str] = None,
) -> list[LibraryItem]:
    saved = []
    for payload in items:
        data = payload.model_dump()
        item = LibraryItem(id=str(uuid.uuid4()), **data, owner_user_id=owner_user_id)
        db.add(item)
        saved.append(item)
    await db.flush()
    return saved


async def seed_library(db: AsyncSession) -> int:
    """Seed system items. Skip if already seeded (idempotent)."""
    existing = await db.execute(
        select(LibraryItem).where(LibraryItem.created_by == "system").limit(1)
    )
    if existing.scalar_one_or_none():
        return 0

    count = 0
    for data in _SEED_DATA:
        db.add(LibraryItem(id=str(uuid.uuid4()), **data))
        count += 1
    await db.flush()
    return count


async def reseed_library(db: AsyncSession) -> int:
    """Delete all system items and re-seed."""
    await db.execute(delete(LibraryItem).where(LibraryItem.created_by == "system"))
    count = 0
    for data in _SEED_DATA:
        db.add(LibraryItem(id=str(uuid.uuid4()), **data))
        count += 1
    await db.flush()
    return count

