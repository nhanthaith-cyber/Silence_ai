from sqlalchemy.orm import Session
from app.models.models import Conversation, Message, Ticket, ConversationStatus, MessageDirection, TicketCategory
from app.core.socket_manager import emit_new_message, emit_conversation_update, emit_ai_typing
from app.services.ai_service import get_ai_response
from datetime import datetime
import uuid
import json


def gen_uuid():
    return str(uuid.uuid4())


async def process_incoming_message(
    platform: str,
    platform_conversation_id: str,
    customer_id: str,
    customer_name: str,
    message_content: str,
    db: Session,
    customer_avatar: str = None,
    image_url: str = None
) -> dict:
    """
    Xử lý tin nhắn đến từ bất kỳ platform nào.
    Pipeline mới:
    1. Tìm hoặc tạo conversation
    2. Lưu message
    3. Load customer memory
    4. Tìm product context (nếu liên quan)
    5. Gọi AI với memory + product context
    6. Xử lý memory updates
    7. Emit real-time events
    """
    # 1. Tìm hoặc tạo conversation
    conversation = db.query(Conversation).filter(
        Conversation.platform == platform,
        Conversation.platform_conversation_id == platform_conversation_id
    ).first()
    
    if not conversation:
        conversation = Conversation(
            id=gen_uuid(),
            platform=platform,
            platform_conversation_id=platform_conversation_id,
            customer_id=customer_id,
            customer_name=customer_name,
            customer_avatar=customer_avatar,
            status=ConversationStatus.OPEN,
            last_message="[Hình ảnh] " + message_content if image_url else message_content,
            last_message_at=datetime.utcnow(),
            unread_count=1
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    else:
        conversation.last_message = "[Hình ảnh] " + message_content if image_url else message_content
        conversation.last_message_at = datetime.utcnow()
        conversation.unread_count = (conversation.unread_count or 0) + 1
        db.commit()
    
    # 2. Lưu tin nhắn của khách
    customer_msg = Message(
        id=gen_uuid(),
        conversation_id=conversation.id,
        direction=MessageDirection.INBOUND,
        sender_name=customer_name,
        content=message_content,
        image_url=image_url,
        is_ai_generated=False
    )
    db.add(customer_msg)
    db.commit()
    db.refresh(customer_msg)
    
    # 3. Emit real-time cho frontend
    msg_data = {
        "id": customer_msg.id,
        "conversation_id": conversation.id,
        "direction": "inbound",
        "content": message_content,
        "image_url": image_url,
        "sender_name": customer_name,
        "is_ai_generated": False,
        "created_at": customer_msg.created_at.isoformat() if customer_msg.created_at else datetime.utcnow().isoformat()
    }
    await emit_new_message(conversation.id, msg_data)
    await emit_conversation_update({
        "id": conversation.id,
        "platform": platform,
        "customer_name": customer_name,
        "last_message": conversation.last_message,
        "unread_count": conversation.unread_count,
        "status": conversation.status
    })
    
    # 4. Gọi AI nếu conversation chưa được nhân viên handle
    if conversation.status in [ConversationStatus.OPEN, ConversationStatus.AI_HANDLING]:
        await emit_ai_typing(conversation.id, True)
        
        # ─── Load customer memory ──────────────────────────────
        customer_memory = None
        try:
            from app.services.memory_service import get_customer_memory
            customer_memory = get_customer_memory(db, customer_id, platform)
        except Exception as e:
            print(f"[Message Service] Memory load error: {e}")
        
        # ─── Tìm product context liên quan ────────────────────
        product_context = None
        try:
            product_context = await _find_product_context(message_content, db)
        except Exception as e:
            print(f"[Message Service] Product context error: {e}")
        
        # ─── Gọi AI với đầy đủ context ────────────────────────
        ai_result = await get_ai_response(
            conversation=conversation,
            user_message=message_content,
            db=db,
            platform=platform,
            customer_memory=customer_memory,
            product_context=product_context,
            image_url=image_url
        )
        
        await emit_ai_typing(conversation.id, False)
        
        # ─── Xử lý memory updates từ AI ───────────────────────
        try:
            memory_updates = ai_result.get("memory_updates")
            if memory_updates:
                from app.services.memory_service import update_customer_memory
                update_customer_memory(db, customer_id, platform, memory_updates)
        except Exception as e:
            print(f"[Message Service] Memory update error: {e}")
        
        # Lưu AI response
        ai_msg = Message(
            id=gen_uuid(),
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            sender_name="AI Assistant",
            content=ai_result["reply"],
            is_ai_generated=True,
            ai_confidence=ai_result["confidence"]
        )
        db.add(ai_msg)
        
        # Cập nhật status conversation
        if ai_result["should_handoff"]:
            conversation.status = ConversationStatus.WAITING_HUMAN
            _create_ticket(
                conversation, 
                ai_result["category"], 
                message_content, 
                db,
                emotion_level=ai_result.get("emotion_level", "neutral"),
                escalation_reason=ai_result.get("escalation_reason")
            )
        else:
            conversation.status = ConversationStatus.AI_HANDLING
        
        conversation.ai_confidence = ai_result["confidence"]
        db.commit()
        db.refresh(ai_msg)
        
        # Emit AI response
        ai_msg_data = {
            "id": ai_msg.id,
            "conversation_id": conversation.id,
            "direction": "outbound",
            "content": ai_result["reply"],
            "sender_name": "AI Assistant",
            "is_ai_generated": True,
            "ai_confidence": ai_result["confidence"],
            "created_at": ai_msg.created_at.isoformat() if ai_msg.created_at else datetime.utcnow().isoformat()
        }
        await emit_new_message(conversation.id, ai_msg_data)
        
        if ai_result["should_handoff"]:
            await emit_conversation_update({
                "id": conversation.id,
                "status": "waiting_human",
                "needs_attention": True
            })
    
    return {"success": True, "conversation_id": conversation.id}


async def _find_product_context(message: str, db: Session) -> str:
    """Tìm sản phẩm liên quan dựa trên nội dung tin nhắn, kèm theo dữ liệu tồn kho thực tế từ Nhanh.vn."""
    try:
        from app.services.product_service import search_products, format_product_for_prompt
        from app.integrations.nhanh import NhanhVNAdapter
        
        # Khởi tạo nhanh_adapter ở đây hoặc lấy từ instance global
        nhanh_adapter = NhanhVNAdapter(
            app_id="77546",
            secret_key="QBjZ2fXGowF53SQo4By6aYapBm5aurxHOW07AGdoubnZomUAr3PQrCEYUK50ex1z60tgcdZpCKh4N5gtlPkODRnvQCiEc6WwyUiPKVsxM5rZcW5r2JMRQe10lW2mN7es"
        )
        
        # Tìm sản phẩm liên quan trong Database cục bộ (lấy thông tin cơ bản)
        products = search_products(db, query=message, limit=3)
        
        # Gọi Nhanh.vn API để lấy tồn kho thực tế
        inventory_data = await nhanh_adapter.check_inventory(message)
        
        context_parts = []
        
        # Thêm thông tin từ Database cục bộ
        if products:
            for p in products[:2]:  # Tối đa 2 sản phẩm
                context_parts.append(format_product_for_prompt(p))
                
        # Thêm thông tin tồn kho thực tế từ Nhanh.vn
        if inventory_data and "data" in inventory_data:
            nhanh_info = ""
            for item in inventory_data["data"]:
                nhanh_info += f"{item.get('sku')} - {item.get('product_name')}\n"
                stock_dict = item.get("available_stock", {})
                for color_or_size, value in stock_dict.items():
                    if isinstance(value, dict):
                        for size, qty in value.items():
                            nhanh_info += f"Màu {color_or_size} - Size {size}: {qty}\n"
                    else:
                        nhanh_info += f"Size {color_or_size}: {value}\n"
            context_parts.append(nhanh_info.strip())
        
        if not context_parts:
            return None
            
        return "\n\n".join(context_parts)
    except ImportError:
        return None
    except Exception as e:
        print(f"[Message Service] Product search error: {e}")
        return None


def _create_ticket(
    conversation: Conversation, 
    category: str, 
    description: str, 
    db: Session,
    emotion_level: str = "neutral",
    escalation_reason: str = None
):
    """Tạo ticket tự động khi AI cần handoff — nâng cấp với emotion và escalation reason."""
    existing = db.query(Ticket).filter(
        Ticket.conversation_id == conversation.id,
        Ticket.status == "open"
    ).first()
    
    if not existing:
        # Xác định priority dựa trên emotion và category
        if emotion_level == "angry" or category == "complaint":
            priority = "high"
        elif emotion_level == "annoyed":
            priority = "high"
        else:
            priority = "normal"
        
        # Thêm escalation reason vào description
        full_description = description
        if escalation_reason:
            full_description = f"{description}\n\n[Lý do escalate] {escalation_reason}"
        
        ticket = Ticket(
            id=gen_uuid(),
            conversation_id=conversation.id,
            category=category,
            priority=priority,
            title=f"[{conversation.platform.upper()}] {conversation.customer_name} - {category}",
            description=full_description,
            status="open"
        )
        db.add(ticket)
        db.commit()
