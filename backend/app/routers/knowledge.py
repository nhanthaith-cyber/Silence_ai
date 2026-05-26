from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.models.models import KnowledgeBase
from datetime import datetime
import uuid

router = APIRouter()


class KnowledgeCreate(BaseModel):
    category: str = "general"
    question: str
    answer: str
    tags: str = ""
    is_active: bool = True


class KnowledgeUpdate(BaseModel):
    category: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    tags: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_knowledge(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(KnowledgeBase)
    if category and category != "all":
        query = query.filter(KnowledgeBase.category == category)
    if search:
        query = query.filter(
            KnowledgeBase.question.ilike(f"%{search}%") |
            KnowledgeBase.answer.ilike(f"%{search}%")
        )
    items = query.order_by(KnowledgeBase.created_at.desc()).all()
    return [_serialize(item) for item in items]


@router.post("")
async def create_knowledge(body: KnowledgeCreate, db: Session = Depends(get_db)):
    item = KnowledgeBase(
        id=str(uuid.uuid4()),
        category=body.category,
        question=body.question,
        answer=body.answer,
        tags=body.tags,
        is_active=body.is_active
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize(item)


@router.put("/{item_id}")
async def update_knowledge(item_id: str, body: KnowledgeUpdate, db: Session = Depends(get_db)):
    item = db.query(KnowledgeBase).filter(KnowledgeBase.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    
    for field, val in body.dict(exclude_none=True).items():
        setattr(item, field, val)
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return _serialize(item)


@router.delete("/{item_id}")
async def delete_knowledge(item_id: str, db: Session = Depends(get_db)):
    item = db.query(KnowledgeBase).filter(KnowledgeBase.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
    return {"success": True}


def _serialize(item: KnowledgeBase) -> dict:
    return {
        "id": item.id,
        "category": item.category,
        "question": item.question,
        "answer": item.answer,
        "tags": item.tags,
        "is_active": item.is_active,
        "usage_count": item.usage_count,
        "created_at": item.created_at.isoformat() if item.created_at else None
    }
