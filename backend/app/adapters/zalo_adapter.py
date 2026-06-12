"""
Zalo OA Adapter
Xử lý webhook từ Zalo OA API
"""
import hmac
import hashlib
import httpx
from app.core.config import settings

def verify_zalo_signature(app_id: str, data: str, timestamp: str, mac: str) -> bool:
    """Xác minh chữ ký webhook từ Zalo OA"""
    if not settings.ZALO_APP_SECRET:
        return True  # Skip verification in development
    
    # Chuỗi data cần hash: <app_id><data><timestamp><secret_key>
    # (Theo doc của Zalo, cấu trúc có thể khác một chút tuỳ API version, ở đây code mẫu chuẩn)
    raw_data = f"{app_id}{data}{timestamp}{settings.ZALO_APP_SECRET}"
    expected = hashlib.sha256(raw_data.encode()).hexdigest()
    return hmac.compare_digest(expected, mac)


def parse_zalo_webhook(body: dict) -> list[dict]:
    """Parse Zalo webhook payload thành danh sách messages chuẩn hóa"""
    messages = []
    
    event_name = body.get("event_name")
    
    if event_name == "user_send_text":
        sender = body.get("sender", {}).get("id")
        message_text = body.get("message", {}).get("text", "")
        message_id = body.get("message", {}).get("msg_id")
        
        if sender and message_text:
            messages.append({
                "platform": "zalo",
                "platform_conversation_id": str(sender),
                "customer_id": f"zalo_{sender}",
                "customer_name": f"Zalo_User_{str(sender)[-6:]}",
                "content": message_text,
                "message_id": message_id
            })
            
    return messages


async def send_zalo_message(recipient_id: str, message_text: str) -> bool:
    """Gửi tin nhắn qua Zalo OA OpenAPI"""
    if not settings.ZALO_ACCESS_TOKEN:
        print(f"[Zalo] Mock send to {recipient_id}: {message_text[:50]}...")
        return True
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://openapi.zalo.me/v2.0/oa/message",
            headers={
                "access_token": settings.ZALO_ACCESS_TOKEN,
                "Content-Type": "application/json"
            },
            json={
                "recipient": {"user_id": recipient_id},
                "message": {"text": message_text}
            }
        )
        data = resp.json()
        if data.get("error") == 0:
            return True
        else:
            print(f"[Zalo] Send message failed: {data}")
            return False

def generate_mock_zalo_message() -> dict:
    """Tạo tin nhắn mock từ Zalo (để test)"""
    import random
    user_id = random.randint(100000, 999999)
    return {
        "platform": "zalo",
        "platform_conversation_id": str(user_id),
        "customer_id": f"zalo_{user_id}",
        "customer_name": f"Zalo_User_{user_id}",
        "content": "Mình muốn lấy 1 áo thun nhé",
        "message_id": f"msg_{random.randint(1000, 9999)}"
    }
