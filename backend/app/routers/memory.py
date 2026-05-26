from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.services.memory_service import (
    get_customer_memory,
    update_customer_memory,
    cleanup_expired_memories,
    memory_to_dict,
)
from app.models.models import CustomerMemory
from datetime import datetime
import uuid

router = APIRouter()


class MemoryUpdate(BaseModel):
    """Schema cập nhật memory khách hàng."""
    platform: str = "all"
    preferred_sizes: Optional[str] = None
    preferred_fit: Optional[str] = None
    style_preferences: Optional[str] = None
    purchase_history_summary: Optional[str] = None
    last_purchase_date: Optional[str] = None
    complaint_history: Optional[str] = None
    price_sensitivity: Optional[str] = None
    satisfaction_score: Optional[float] = None
    communication_style: Optional[str] = None
    body_measurements: Optional[str] = None
    notes: Optional[str] = None


@router.get("")
async def list_memories(
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Liệt kê tất cả customer memories, có thể lọc theo customer_id."""
    query = db.query(CustomerMemory)
    if customer_id:
        query = query.filter(CustomerMemory.customer_id.ilike(f"%{customer_id}%"))
    items = query.order_by(CustomerMemory.updated_at.desc()).all()
    return [memory_to_dict(item) for item in items]


@router.get("/{customer_id}")
async def get_memory(
    customer_id: str,
    platform: str = "all",
    db: Session = Depends(get_db)
):
    """Lấy memory của một khách hàng cụ thể."""
    memory = get_customer_memory(db, customer_id, platform)
    if not memory:
        raise HTTPException(status_code=404, detail="Chưa có memory cho khách hàng này")
    return memory


@router.put("/{customer_id}")
async def upsert_memory(
    customer_id: str,
    body: MemoryUpdate,
    db: Session = Depends(get_db)
):
    """Cập nhật hoặc tạo mới memory cho khách hàng."""
    updates = body.dict(exclude_none=True)
    platform = updates.pop("platform", "all")

    # Chuyển last_purchase_date từ string sang datetime nếu có
    if "last_purchase_date" in updates:
        try:
            updates["last_purchase_date"] = datetime.fromisoformat(updates["last_purchase_date"])
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="last_purchase_date phải đúng định dạng ISO (VD: 2025-05-15T00:00:00)")

    result = update_customer_memory(db, customer_id, platform, updates)
    return result


@router.delete("/{customer_id}")
async def delete_memory(
    customer_id: str,
    platform: str = "all",
    db: Session = Depends(get_db)
):
    """Xóa memory của khách hàng."""
    memory = db.query(CustomerMemory).filter(
        CustomerMemory.customer_id == customer_id,
        CustomerMemory.platform == platform
    ).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Không tìm thấy memory")
    db.delete(memory)
    db.commit()
    return {"success": True}


@router.post("/cleanup")
async def trigger_cleanup(db: Session = Depends(get_db)):
    """Xóa tất cả memories đã hết hạn."""
    count = cleanup_expired_memories(db)
    return {"success": True, "deleted_count": count}
