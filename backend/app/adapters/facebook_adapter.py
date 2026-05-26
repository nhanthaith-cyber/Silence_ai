"""
Facebook Messenger Adapter
Xử lý webhook từ Facebook Messenger API
"""
import hmac
import hashlib
import httpx
from app.core.config import settings


def verify_facebook_signature(payload: bytes, signature: str) -> bool:
    """Xác minh chữ ký webhook từ Facebook"""
    if not settings.FACEBOOK_APP_SECRET:
        return True  # Skip verification in development
    expected = hmac.new(
        settings.FACEBOOK_APP_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def parse_facebook_webhook(body: dict) -> list[dict]:
    """Parse Facebook webhook payload thành danh sách messages chuẩn hóa"""
    messages = []
    
    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            if "message" in event and not event["message"].get("is_echo"):
                sender_id = event["sender"]["id"]
                message_text = event["message"].get("text", "")
                
                if message_text:
                    messages.append({
                        "platform": "facebook",
                        "platform_conversation_id": sender_id,
                        "customer_id": sender_id,
                        "customer_name": f"FB_{sender_id[-6:]}",
                        "content": message_text,
                        "message_id": event["message"].get("mid")
                    })
    
    return messages


async def send_facebook_message(recipient_id: str, message_text: str) -> bool:
    """Gửi tin nhắn qua Facebook Messenger API"""
    if not settings.FACEBOOK_PAGE_TOKEN:
        print(f"[Facebook] Mock send to {recipient_id}: {message_text[:50]}...")
        return True
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://graph.facebook.com/v19.0/me/messages",
            params={"access_token": settings.FACEBOOK_PAGE_TOKEN},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": message_text}
            }
        )
        return resp.status_code == 200
