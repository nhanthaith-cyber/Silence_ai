"""
Shopee Chat Polling Service
Tự động kiểm tra tin nhắn mới từ Shopee mỗi 30 giây (thay thế Push webhook)
"""
import asyncio
import time
from typing import Set
from app.core.database import SessionLocal
from app.adapters.shopee_adapter import shopee_client


# Lưu message_id đã xử lý (in-memory) để tránh trùng
_processed_message_ids: Set[str] = set()
_MAX_PROCESSED_CACHE = 5000  # Giới hạn cache
_polling_active = False

POLL_INTERVAL = 30  # giây


async def start_shopee_polling():
    """Khởi động vòng lặp polling Shopee Chat"""
    global _polling_active
    _polling_active = True
    print("[Shopee Polling] >> Starting Shopee Chat polling (every 30s)...")
    
    # Đợi 10 giây cho server khởi động xong
    await asyncio.sleep(10)
    
    while _polling_active:
        try:
            await _poll_shopee_messages()
        except Exception as e:
            print(f"[Shopee Polling] ERROR: {e}")
        
        await asyncio.sleep(POLL_INTERVAL)


async def stop_shopee_polling():
    """Dừng polling"""
    global _polling_active
    _polling_active = False
    print("[Shopee Polling] Stopped")


async def _poll_shopee_messages():
    """Kiểm tra tin nhắn mới từ tất cả cuộc hội thoại Shopee"""
    db = SessionLocal()
    try:
        # 1. Kiểm tra có token Shopee không
        token_info = await shopee_client.get_valid_token(db)
        if not token_info:
            return  # Chưa kết nối Shopee
        
        shop_id = str(token_info["shop_id"])
        
        # 2. Lấy danh sách cuộc hội thoại gần đây
        conv_result = await shopee_client.get_conversations(db, direction="latest", page_size=15)
        
        if conv_result.get("error"):
            print(f"[Shopee Polling] API error: {conv_result}")
            return
        
        conversations = conv_result.get("response", {}).get("conversations", [])
        if not conversations:
            return
        
        # 3. Kiểm tra từng cuộc hội thoại có tin nhắn mới không
        new_count = 0
        for conv in conversations:
            conv_id = str(conv.get("conversation_id", ""))
            # Chỉ xử lý cuộc hội thoại có tin nhắn mới (unread)
            if not conv.get("unread_count", 0) and not conv.get("last_read_message_id"):
                # Vẫn kiểm tra nếu có last_message_id mới
                pass
            
            # 4. Lấy tin nhắn mới nhất
            msg_result = await shopee_client.get_messages(db, conv_id, page_size=5)
            if msg_result.get("error"):
                continue
            
            messages = msg_result.get("response", {}).get("messages", [])
            
            for msg in messages:
                msg_id = str(msg.get("message_id", ""))
                sender_id = str(msg.get("from_id", ""))
                
                # Bỏ qua tin nhắn đã xử lý
                if msg_id in _processed_message_ids:
                    continue
                
                # Bỏ qua tin nhắn từ chính shop
                if sender_id == shop_id:
                    _processed_message_ids.add(msg_id)
                    continue
                
                # Bỏ qua tin nhắn cũ hơn 5 phút
                msg_time = msg.get("created_timestamp", 0)
                if msg_time and (time.time() - msg_time) > 300:
                    _processed_message_ids.add(msg_id)
                    continue
                
                # 5. Xử lý tin nhắn mới!
                content = ""
                msg_type = msg.get("message_type", "text")
                if msg_type == "text":
                    content = msg.get("content", {}).get("text", "")
                elif msg_type == "image":
                    content = "[Hình ảnh]"
                elif msg_type == "sticker":
                    content = "[Sticker]"
                else:
                    content = f"[{msg_type}]"
                
                if content:
                    from app.services.message_service import process_incoming_message
                    
                    # Lấy tên khách (nếu có)
                    buyer_name = msg.get("from_user_name", f"Shopee_{sender_id[-4:]}")
                    
                    print(f"[Shopee Polling] New message from {buyer_name}: {content[:50]}...")
                    
                    await process_incoming_message(
                        platform="shopee",
                        platform_conversation_id=f"shopee_{conv_id}",
                        customer_id=sender_id,
                        customer_name=buyer_name,
                        message_content=content,
                        db=db
                    )
                    new_count += 1
                
                # Đánh dấu đã xử lý
                _processed_message_ids.add(msg_id)
        
        # Dọn cache nếu quá lớn
        if len(_processed_message_ids) > _MAX_PROCESSED_CACHE:
            # Giữ lại 1000 message_id gần nhất
            excess = len(_processed_message_ids) - 1000
            for _ in range(excess):
                _processed_message_ids.pop()
        
        if new_count > 0:
            print(f"[Shopee Polling] OK Processed {new_count} new messages")
            
    except Exception as e:
        print(f"[Shopee Polling] ERROR Poll error: {e}")
    finally:
        db.close()
