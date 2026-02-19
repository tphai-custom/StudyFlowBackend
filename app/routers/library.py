import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LibraryItemModel

router = APIRouter(prefix="/library", tags=["library"])


class LibraryItemSchema(BaseModel):
    id: Optional[str] = None
    subject: str
    level: str = ""
    title: str
    summary: str = ""
    url: Optional[str] = None
    tags: List[str] = []


def item_to_dict(i: LibraryItemModel) -> dict:
    return {
        "id": i.id,
        "subject": i.subject,
        "level": i.level,
        "title": i.title,
        "summary": i.summary,
        "url": i.url,
        "tags": i.tags or [],
    }


@router.get("/")
def list_library(
    q: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(LibraryItemModel)
    items = query.all()
    if subject:
        items = [i for i in items if i.subject.lower() == subject.lower()]
    if q:
        q_lower = q.lower()
        items = [
            i for i in items
            if q_lower in i.title.lower() or q_lower in i.summary.lower()
        ]
    return [item_to_dict(i) for i in items]


@router.post("/", status_code=201)
def bulk_save_library(items: List[LibraryItemSchema], db: Session = Depends(get_db)):
    db.query(LibraryItemModel).delete()
    saved = []
    for item in items:
        lib_item = LibraryItemModel(
            id=item.id if item.id else str(uuid.uuid4()),
            subject=item.subject,
            level=item.level,
            title=item.title,
            summary=item.summary,
            url=item.url,
            tags=item.tags,
        )
        db.add(lib_item)
        saved.append(lib_item)
    db.commit()
    for lib_item in saved:
        db.refresh(lib_item)
    return [item_to_dict(i) for i in saved]
