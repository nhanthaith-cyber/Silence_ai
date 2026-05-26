from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.models.models import Ticket, Conversation
import uuid

router = APIRouter()


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    assigned_agent: Optional[str] = None
    priority: Optional[str] = None
    resolution: Optional[str] = None


@router.get("/stats")
async def get_ticket_stats(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
    if category and category != "all":
        query = query.filter(Ticket.category == category)
    
    stats_result = query.all()
    stats = {"open": 0, "in_progress": 0, "resolved": 0, "closed": 0, "total": 0}
    for status, count in stats_result:
        stats[status] = count
        stats["total"] += count
    
    return stats


@router.get("")
async def list_tickets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Ticket)
    if status and status != "all":
        query = query.filter(Ticket.status == status)
    if category and category != "all":
        query = query.filter(Ticket.category == category)
    if priority:
        query = query.filter(Ticket.priority == priority)
    
    tickets = query.order_by(desc(Ticket.created_at)).all()
    return [_serialize(t) for t in tickets]


@router.patch("/{ticket_id}")
async def update_ticket(ticket_id: str, body: TicketUpdate, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    for field, val in body.dict(exclude_none=True).items():
        setattr(ticket, field, val)
    db.commit()
    db.refresh(ticket)
    return _serialize(ticket)


def _serialize(t: Ticket) -> dict:
    customer_name = t.conversation.customer_name if t.conversation else "Khách hàng ẩn danh"
    return {
        "id": t.id,
        "conversation_id": t.conversation_id,
        "customer_name": customer_name,
        "category": t.category,
        "priority": t.priority,
        "title": t.title,
        "description": t.description,
        "status": t.status,
        "assigned_agent": t.assigned_agent,
        "resolution": t.resolution,
        "created_at": t.created_at.isoformat() if t.created_at else None
    }
