"""
Instagram DM Adapter  
Instagram dùng chung Meta Graph API với Facebook
"""
import httpx
from app.core.config import settings


def parse_instagram_webhook(body: dict) -> list[dict]:
    """Parse Instagram webhook payload"""
    messages = []
    
    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            if "message" in event and not event["message"].get("is_echo"):
                sender_id = event["sender"]["id"]
                message_text = event["message"].get("text", "")
                
                if message_text:
                    messages.append({
                        "platform": "instagram",
                        "platform_conversation_id": sender_id,
                        "customer_id": sender_id,
                        "customer_name": f"IG_{sender_id[-6:]}",
                        "content": message_text,
                        "message_id": event["message"].get("mid")
                    })
    
    return messages


async def send_instagram_message(recipient_id: str, message_text: str) -> bool:
    """Gửi tin nhắn qua Instagram DM"""
    token = settings.INSTAGRAM_ACCESS_TOKEN or settings.FACEBOOK_PAGE_TOKEN
    
    if not token:
        print(f"[Instagram] Mock send to {recipient_id}: {message_text[:50]}...")
        return True
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://graph.facebook.com/v19.0/me/messages",
            params={"access_token": token},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": message_text}
            }
        )
        return resp.status_code == 200
