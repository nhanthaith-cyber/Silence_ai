from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.models import Conversation, Message, Ticket, ConversationStatus, PlatformEnum

router = APIRouter()


@router.get("/overview")
async def get_overview(db: Session = Depends(get_db)):
    """Thống kê tổng quan cho dashboard"""
    total_conversations = db.query(Conversation).count()
    open_conversations = db.query(Conversation).filter(
        Conversation.status.in_([ConversationStatus.OPEN, ConversationStatus.AI_HANDLING])
    ).count()
    waiting_human = db.query(Conversation).filter(
        Conversation.status == ConversationStatus.WAITING_HUMAN
    ).count()
    resolved_today = db.query(Conversation).filter(
        Conversation.status == ConversationStatus.RESOLVED
    ).count()
    
    total_messages = db.query(Message).count()
    ai_messages = db.query(Message).filter(Message.is_ai_generated == True).count()
    
    ai_rate = round(ai_messages / total_messages * 100, 1) if total_messages > 0 else 0
    
    # Phân bổ theo platform
    platform_stats = []
    for platform in ["facebook", "instagram", "shopee", "tiktok"]:
        count = db.query(Conversation).filter(Conversation.platform == platform).count()
        platform_stats.append({"platform": platform, "count": count})
    
    # Status distribution
    status_stats = []
    for status in ConversationStatus:
        count = db.query(Conversation).filter(Conversation.status == status).count()
        status_stats.append({"status": status.value, "count": count})
    
    return {
        "total_conversations": total_conversations,
        "open_conversations": open_conversations,
        "waiting_human": waiting_human,
        "resolved_today": resolved_today,
        "total_messages": total_messages,
        "ai_messages": ai_messages,
        "ai_auto_reply_rate": ai_rate,
        "platform_stats": platform_stats,
        "status_stats": status_stats
    }


@router.get("/tickets")
async def get_ticket_stats(db: Session = Depends(get_db)):
    """Thống kê tickets"""
    from app.models.models import Ticket
    
    total = db.query(Ticket).count()
    open_tickets = db.query(Ticket).filter(Ticket.status == "open").count()
    resolved = db.query(Ticket).filter(Ticket.status == "resolved").count()
    
    by_category = db.query(Ticket.category, func.count(Ticket.id)).group_by(Ticket.category).all()
    by_priority = db.query(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority).all()
    
    return {
        "total": total,
        "open": open_tickets,
        "resolved": resolved,
        "by_category": [{"category": c, "count": n} for c, n in by_category],
        "by_priority": [{"priority": p, "count": n} for p, n in by_priority]
    }
