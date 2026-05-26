from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.models.models import Conversation, Message, ConversationStatus, MessageDirection
from app.core.socket_manager import emit_new_message, emit_conversation_update
from datetime import datetime
import uuid
import base64
import os

router = APIRouter()

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

class SendMessageRequest(BaseModel):
    content: str
    is_ai: bool = False
    image_base64: Optional[str] = None

class HandoffRequest(BaseModel):
    agent_name: str
    note: Optional[str] = None

def _save_base64_image(base64_str: str) -> str:
    """Lưu ảnh base64 vào thư mục uploads/ và trả về đường dẫn tĩnh"""
    if not base64_str:
        return None
    try:
        # Xử lý data url: "data:image/png;base64,iVBORw0KGgo..."
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
            
        image_data = base64.b64decode(base64_str)
        filename = f"{uuid.uuid4().hex}.png"
        filepath = os.path.join("uploads", filename)
        
        with open(filepath, "wb") as f:
            f.write(image_data)
            
        return f"/uploads/{filename}"
    except Exception as e:
        print(f"Error saving image: {e}")
        return None

@router.get("")
async def list_conversations(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Lấy danh sách conversations (Unified Inbox)"""
    query = db.query(Conversation)
    
    if platform and platform != "all":
        query = query.filter(Conversation.platform == platform)
    if status and status != "all":
        query = query.filter(Conversation.status == status)
    if search:
        query = query.filter(
            Conversation.customer_name.ilike(f"%{search}%") |
            Conversation.last_message.ilike(f"%{search}%")
        )
    
    total = query.count()
    conversations = query.order_by(desc(Conversation.last_message_at)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [_serialize_conversation(c) for c in conversations]
    }

@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Lấy chi tiết 1 conversation"""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Reset unread
    conv.unread_count = 0
    db.commit()
    
    return _serialize_conversation(conv)

@router.get("/{conversation_id}/messages")
async def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    """Lấy tin nhắn của 1 conversation"""
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()
    
    return [_serialize_message(m) for m in messages]

@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    db: Session = Depends(get_db)
):
    """Nhân viên gửi tin nhắn thủ công"""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    image_url = _save_base64_image(body.image_base64)
    
    msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        direction=MessageDirection.OUTBOUND,
        sender_name="Nhân viên" if not body.is_ai else "AI Assistant",
        content=body.content,
        image_url=image_url,
        is_ai_generated=body.is_ai
    )
    db.add(msg)
    
    conv.last_message = "[Hình ảnh] " + body.content if image_url else body.content
    conv.last_message_at = datetime.utcnow()
    db.commit()
    db.refresh(msg)
    
    msg_data = _serialize_message(msg)
    await emit_new_message(conversation_id, msg_data)
    
    return msg_data

class MockInboundRequest(BaseModel):
    content: str
    image_base64: Optional[str] = None

@router.post("/{conversation_id}/mock-inbound")
async def mock_inbound_message(
    conversation_id: str,
    body: MockInboundRequest,
    db: Session = Depends(get_db)
):
    """Giả lập khách hàng gửi tin nhắn vào đoạn chat này"""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    from app.services.message_service import process_incoming_message
    
    # Reset status về OPEN để AI có thể xử lý
    conv.status = ConversationStatus.OPEN
    db.commit()
    
    image_url = _save_base64_image(body.image_base64)

    result = await process_incoming_message(
        platform=conv.platform,
        platform_conversation_id=conv.platform_conversation_id,
        customer_id=conv.customer_id,
        customer_name=conv.customer_name,
        message_content=body.content,
        db=db,
        customer_avatar=conv.customer_avatar,
        image_url=image_url
    )
    return result

@router.post("/{conversation_id}/handoff")
async def handoff_to_human(
    conversation_id: str,
    body: HandoffRequest,
    db: Session = Depends(get_db)
):
    """Chuyển tay conversation sang nhân viên"""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv.status = ConversationStatus.HUMAN_HANDLING
    conv.assigned_agent = body.agent_name
    db.commit()
    
    # Thêm system message
    sys_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        direction=MessageDirection.OUTBOUND,
        sender_name="Hệ thống",
        content=f"✅ Đã chuyển cho nhân viên {body.agent_name}" + (f". Ghi chú: {body.note}" if body.note else ""),
        is_ai_generated=False
    )
    db.add(sys_msg)
    db.commit()
    
    await emit_conversation_update({
        "id": conversation_id,
        "status": "human_handling",
        "assigned_agent": body.agent_name
    })
    
    return {"success": True, "assigned_to": body.agent_name}

@router.patch("/{conversation_id}/resolve")
async def resolve_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Đánh dấu conversation đã giải quyết"""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv.status = ConversationStatus.RESOLVED
    db.commit()
    
    await emit_conversation_update({"id": conversation_id, "status": "resolved"})
    return {"success": True}

def _serialize_conversation(c: Conversation) -> dict:
    return {
        "id": c.id,
        "platform": c.platform,
        "customer_id": c.customer_id,
        "customer_name": c.customer_name,
        "customer_avatar": c.customer_avatar,
        "status": c.status,
        "assigned_agent": c.assigned_agent,
        "last_message": c.last_message,
        "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
        "unread_count": c.unread_count or 0,
        "ai_confidence": c.ai_confidence,
        "created_at": c.created_at.isoformat() if c.created_at else None
    }

def _serialize_message(m: Message) -> dict:
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "direction": m.direction,
        "sender_name": m.sender_name,
        "content": m.content,
        "image_url": m.image_url,
        "is_ai_generated": m.is_ai_generated,
        "ai_confidence": m.ai_confidence,
        "created_at": m.created_at.isoformat() if m.created_at else None
    }
