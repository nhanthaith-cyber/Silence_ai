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
        
        # ─── CHECK ORDER FLOW ─────────────────────────────────
        try:
            order_reply = await _handle_order_flow(conversation, message_content, db)
            if order_reply:
                await emit_ai_typing(conversation.id, False)
                
                # Lưu AI response cho order flow
                ai_msg = Message(
                    id=gen_uuid(),
                    conversation_id=conversation.id,
                    direction=MessageDirection.OUTBOUND,
                    sender_name="AI Assistant",
                    content=order_reply,
                    is_ai_generated=True,
                    ai_confidence=0.95
                )
                db.add(ai_msg)
                conversation.status = ConversationStatus.AI_HANDLING
                conversation.ai_confidence = 0.95
                db.commit()
                db.refresh(ai_msg)
                
                ai_msg_data = {
                    "id": ai_msg.id,
                    "conversation_id": conversation.id,
                    "direction": "outbound",
                    "content": order_reply,
                    "sender_name": "AI Assistant",
                    "is_ai_generated": True,
                    "ai_confidence": 0.95,
                    "created_at": ai_msg.created_at.isoformat() if ai_msg.created_at else datetime.utcnow().isoformat()
                }
                await emit_new_message(conversation.id, ai_msg_data)
                
                # Gửi reply về platform
                try:
                    await _send_reply_to_platform(
                        platform=platform,
                        conversation=conversation,
                        reply_text=order_reply,
                        db=db
                    )
                except Exception as e:
                    print(f"[Message Service] Platform send error: {e}")
                
                return {"success": True, "conversation_id": conversation.id}
        except Exception as e:
            print(f"[Message Service] Order flow error: {e}")
        
        # ─── NORMAL AI FLOW ───────────────────────────────────
        # Load customer memory
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
        
        # ─── GỬI AI REPLY NGƯỢC VỀ PLATFORM CHO KHÁCH ─────────
        try:
            await _send_reply_to_platform(
                platform=platform,
                conversation=conversation,
                reply_text=ai_result["reply"],
                db=db
            )
        except Exception as e:
            print(f"[Message Service] Platform send error: {e}")
    
    return {"success": True, "conversation_id": conversation.id}


async def _send_reply_to_platform(platform: str, conversation, reply_text: str, db):
    """Gửi tin nhắn AI trả lời ngược về platform cho khách hàng."""
    if platform == "shopee":
        from app.adapters.shopee_adapter import send_shopee_message
        # conversation.platform_conversation_id = "shopee_{conversation_id}"
        # Shopee send_message cần to_id = buyer user id
        buyer_id = conversation.customer_id
        success = await send_shopee_message(buyer_id, reply_text, db=db)
        if success:
            print(f"[Shopee] ✅ Sent AI reply to {buyer_id}")
        else:
            print(f"[Shopee] ❌ Failed to send reply to {buyer_id}")
    
    elif platform == "facebook":
        try:
            from app.adapters.facebook_adapter import send_facebook_message
            await send_facebook_message(conversation.customer_id, reply_text)
            print(f"[Facebook] ✅ Sent AI reply to {conversation.customer_id}")
        except Exception as e:
            print(f"[Facebook] Send error: {e}")
    
    elif platform == "instagram":
        try:
            from app.adapters.instagram_adapter import send_instagram_message
            await send_instagram_message(conversation.customer_id, reply_text)
            print(f"[Instagram] ✅ Sent AI reply to {conversation.customer_id}")
        except Exception as e:
            print(f"[Instagram] Send error: {e}")
    
    elif platform == "zalo":
        try:
            from app.adapters.zalo_adapter import send_zalo_message
            # Zalo uses customer_id like "zalo_12345", so we need to extract the actual ID
            # In parse_zalo_webhook, we set customer_id = f"zalo_{sender}"
            zalo_user_id = str(conversation.customer_id).replace("zalo_", "")
            
            # Send message via Zalo API
            success = await send_zalo_message(zalo_user_id, reply_text)
            if success:
                print(f"[Zalo] ✅ Sent AI reply to {zalo_user_id}")
            else:
                print(f"[Zalo] ❌ Failed to send reply to {zalo_user_id}")
        except Exception as e:
            print(f"[Zalo] Send error: {e}")
            
    else:
        print(f"[{platform}] Platform send not implemented yet")

async def _find_product_context(message: str, db: Session) -> str:
    """Tìm sản phẩm liên quan dựa trên nội dung tin nhắn, kèm theo dữ liệu tồn kho thực tế từ Nhanh.vn."""
    try:
        from app.services.product_service import search_products, format_product_for_prompt
        from app.integrations.nhanh import NhanhVNAdapter
        
        # Khởi tạo nhanh_adapter ở đây với DB
        nhanh_adapter = NhanhVNAdapter(db=db)
        
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
        
        # Tích hợp thêm Shopee Order context (nếu có mã đơn)
        import re
        order_matches = re.findall(r"(?:đơn|mã|order)?\s*([A-Z0-9]{12,15})", message.upper())
        if order_matches:
            from app.adapters.shopee_adapter import shopee_client
            try:
                for order_sn in order_matches:
                    order_data = await shopee_client.get_order_detail(db, order_sn_list=[order_sn])
                    if order_data and order_data.get("response") and order_data["response"].get("order_list"):
                        order = order_data["response"]["order_list"][0]
                        shopee_info = f"Shopee Order {order_sn}: Status={order.get('order_status')}, Carrier={order.get('shipping_carrier')}\n"
                        context_parts.append(shopee_info)
            except Exception as e:
                print(f"[Message Service] Shopee API error: {e}")
        
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


async def _handle_order_flow(conversation, message: str, db) -> str | None:
    """
    Xử lý order flow trong chat.
    Returns: reply string nếu đang trong order flow, None nếu không.
    """
    from app.services.order_state import (
        is_in_order_flow, get_order_state, start_order_flow,
        update_order_state, cancel_order_flow, complete_order_flow,
        get_missing_fields, format_order_summary, get_prompt_for_missing,
        parse_order_intent, parse_customer_info, parse_confirmation,
        ORDER_STATES
    )
    
    conv_id = conversation.id
    
    # ─── Nếu đang trong order flow ──────────────────────────
    if is_in_order_flow(conv_id):
        state = get_order_state(conv_id)
        current = state["state"]
        
        # Check hủy đơn
        cancel_words = ["hủy", "thôi", "bỏ", "cancel", "dừng", "không mua"]
        if any(w in message.lower() for w in cancel_words) and current != ORDER_STATES["CONFIRMING"]:
            cancel_order_flow(conv_id)
            return "Dạ, em đã hủy đơn hàng. Anh/chị cần hỗ trợ gì thêm không ạ? 😊"
        
        # ─── CONFIRMING state ──────────────────────────────
        if current == ORDER_STATES["CONFIRMING"]:
            confirmed = parse_confirmation(message)
            if confirmed is True:
                # Tạo đơn trên Nhanh.vn
                update_order_state(conv_id, {"state": ORDER_STATES["CREATING"]})
                
                result = await _create_nhanh_order(state, db)
                
                if result["status"] == "success":
                    complete_order_flow(conv_id)
                    order_id = result.get("order_id", "N/A")
                    return f"✅ Đã tạo đơn hàng thành công!\n\n📦 Mã đơn: {order_id}\n🛍️ Sản phẩm: {state['product_name']} - Size {state['size']}\n💰 Tổng: {(state.get('product_price', 0) or 0) * state.get('quantity', 1):,}₫\n\nĐơn hàng đã được ghi nhận trên hệ thống. Em sẽ xử lý và giao hàng sớm nhất cho anh/chị nhé! 🚚"
                else:
                    complete_order_flow(conv_id)
                    return f"⚠️ Đã ghi nhận đơn hàng nhưng chưa đồng bộ được lên hệ thống: {result.get('message', '')}.\n\nEm sẽ xử lý thủ công cho anh/chị nhé. Thông tin:\n- SP: {state['product_name']} Size {state['size']} x{state['quantity']}\n- Người nhận: {state['customer_name']} - {state['customer_phone']}\n- Địa chỉ: {state['address']}"
            
            elif confirmed is False:
                cancel_order_flow(conv_id)
                return "Dạ, em đã hủy đơn hàng. Anh/chị muốn thay đổi thông tin gì không ạ?"
            else:
                return "Anh/chị xác nhận đặt đơn hàng trên không ạ? (Trả lời 'Đồng ý' hoặc 'Hủy')"
        
        # ─── COLLECTING states ─────────────────────────────
        # Parse thông tin từ tin nhắn
        info = parse_customer_info(message)
        
        # Cũng check nếu khách bổ sung product/size
        order_info = parse_order_intent(message)
        if order_info.get("size") and not state.get("size"):
            info["size"] = order_info["size"]
        if order_info.get("product_name") and not state.get("product_name"):
            info["product_name"] = order_info["product_name"]
        
        # Update state
        if info:
            update_order_state(conv_id, info)
        
        # Check missing fields
        missing = get_missing_fields(conv_id)
        
        if not missing:
            # Đã đủ thông tin → tìm sản phẩm trên Nhanh.vn và chuyển sang confirm
            state = get_order_state(conv_id)
            
            # Tìm sản phẩm trên Nhanh.vn để lấy ID và giá
            if not state.get("product_id"):
                try:
                    from app.integrations.nhanh import NhanhVNAdapter
                    nhanh = NhanhVNAdapter(db=db)
                    product = await nhanh.search_product_for_order(state["product_name"])
                    if product:
                        update_order_state(conv_id, {
                            "product_id": product["id"],
                            "product_price": product.get("price", 0),
                            "product_sku": product.get("sku", "")
                        })
                except Exception as e:
                    print(f"[Order] Product search error: {e}")
            
            update_order_state(conv_id, {"state": ORDER_STATES["CONFIRMING"]})
            return format_order_summary(conv_id)
        else:
            return get_prompt_for_missing(missing)
    
    # ─── Chưa trong order flow → kiểm tra intent ────────────
    order_info = parse_order_intent(message)
    if order_info.get("wants_order"):
        # Bắt đầu order flow
        start_order_flow(
            conv_id,
            product_name=order_info.get("product_name"),
            size=order_info.get("size"),
            quantity=order_info.get("quantity", 1)
        )
        
        # Tìm sản phẩm trên Nhanh.vn nếu có tên
        if order_info.get("product_name"):
            try:
                from app.integrations.nhanh import NhanhVNAdapter
                nhanh = NhanhVNAdapter(db=db)
                product = await nhanh.search_product_for_order(order_info["product_name"])
                if product:
                    update_order_state(conv_id, {
                        "product_id": product["id"],
                        "product_price": product.get("price", 0),
                        "product_sku": product.get("sku", ""),
                        "product_name": product.get("name", order_info["product_name"])
                    })
                    
                    reply = f"Dạ, em tìm thấy sản phẩm: **{product['name']}** - Giá: {product.get('price', 0):,}₫\n\n"
                else:
                    reply = f"Dạ, em ghi nhận sản phẩm: **{order_info['product_name']}**\n\n"
            except Exception as e:
                print(f"[Order] Product search error: {e}")
                reply = f"Dạ, em ghi nhận sản phẩm: **{order_info['product_name']}**\n\n"
        else:
            reply = "Dạ, anh/chị muốn đặt hàng! "
        
        missing = get_missing_fields(conv_id)
        if missing:
            reply += get_prompt_for_missing(missing)
        else:
            update_order_state(conv_id, {"state": ORDER_STATES["CONFIRMING"]})
            reply = format_order_summary(conv_id)
        
        return reply
    
    return None  # Không phải order flow


async def _create_nhanh_order(state: dict, db) -> dict:
    """Tạo đơn hàng trên Nhanh.vn từ order state."""
    try:
        from app.integrations.nhanh import NhanhVNAdapter
        nhanh = NhanhVNAdapter(db=db)
        
        products = []
        if state.get("product_id"):
            products.append({
                "id": state["product_id"],
                "quantity": state.get("quantity", 1),
                "price": state.get("product_price", 0)
            })
        
        order_data = {
            "customer_name": state.get("customer_name", ""),
            "customer_phone": state.get("customer_phone", ""),
            "address": state.get("address", ""),
            "products": products,
            "note": state.get("note", f"Đơn từ AI Chat - {state.get('product_name', '')} Size {state.get('size', '')} x{state.get('quantity', 1)}")
        }
        
        result = await nhanh.create_order(order_data)
        return result
    except Exception as e:
        print(f"[Order] Create order error: {e}")
        return {"status": "error", "message": str(e)}
