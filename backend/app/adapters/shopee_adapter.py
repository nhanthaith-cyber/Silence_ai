"""
Shopee Adapter (Mock trong MVP)
Shopee Open Platform không có webhook chat công khai,
sử dụng mock data để demo. Tích hợp thật khi có API access.
"""
import random
from datetime import datetime
import hmac
import hashlib
import time
from app.core.config import settings

SHOPEE_SAMPLE_MESSAGES = [
    "Shop ơi, đơn hàng #{order_id} của mình bao giờ giao vậy?",
    "Mình muốn đổi size áo, shop có hỗ trợ không?",
    "Sản phẩm nhận được bị lỗi, mình xử lý thế nào?",
    "Giá sản phẩm này còn giảm không shop?",
    "Shop giao hàng khu vực Quận 7 không?",
    "Mình cần hóa đơn VAT, shop xuất được không?",
    "Đặt hàng xong có thể hủy không ạ?",
    "Sản phẩm có bảo hành không shop?",
]

SHOPEE_CUSTOMER_NAMES = [
    "Nguyễn Thị Lan", "Trần Văn Nam", "Lê Thị Hoa", "Phạm Văn Đức",
    "Hoàng Thị Mai", "Vũ Văn Hùng", "Đặng Thị Thu", "Bùi Văn Long"
]


def generate_shopee_signature(api_path: str, params: dict = None) -> tuple:
    """Tạo chữ ký HMAC-SHA256 theo chuẩn Shopee Open Platform"""
    partner_id = settings.SHOPEE_PARTNER_ID
    partner_key = settings.SHOPEE_PARTNER_KEY
    timestamp = int(time.time())
    
    # Base string: partner_id + api_path + timestamp + access_token(if any) + shop_id(if any)
    # Với API Auth, chưa có token và shop_id
    base_string = f"{partner_id}{api_path}{timestamp}"
    if params and 'access_token' in params:
        base_string += params['access_token']
    if params and 'shop_id' in params:
        base_string += str(params['shop_id'])
        
    sign = hmac.new(
        partner_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return sign, timestamp


def parse_shopee_webhook(payload: dict) -> list:
    """Phân tích payload từ Shopee Open Platform Push Mechanism"""
    messages = []
    
    # Payload Shopee Push thường có cấu trúc:
    # {
    #   "code": 1,
    #   "shop_id": 123456,
    #   "timestamp": 123456789,
    #   "data": { "message_type": "...", "content": { "text": "..." }, ... }
    # }
    
    code = payload.get("code")
    # Code 1 là chat push event
    if code == 1:
        data = payload.get("data", {})
        sender_id = data.get("from_id", "unknown")
        
        # Bỏ qua tin nhắn từ chính shop
        shop_id = payload.get("shop_id")
        if str(sender_id) == str(shop_id):
            return messages
            
        content_dict = data.get("content", {})
        text_content = content_dict.get("text", "")
        
        if text_content:
            messages.append({
                "platform": "shopee",
                "platform_conversation_id": f"shopee_conv_{sender_id}",
                "customer_id": str(sender_id),
                "customer_name": f"Shopee_{str(sender_id)[-4:]}",
                "content": text_content,
                "message_id": data.get("message_id", f"msg_{random.randint(1000, 9999)}")
            })
            
    return messages


def generate_mock_shopee_message() -> dict:
    """Tạo tin nhắn mock từ Shopee"""
    customer_idx = random.randint(0, len(SHOPEE_CUSTOMER_NAMES) - 1)
    customer_name = SHOPEE_CUSTOMER_NAMES[customer_idx]
    customer_id = f"shopee_user_{1000 + customer_idx}"
    order_id = f"SHOP{random.randint(10000, 99999)}"
    
    message_template = random.choice(SHOPEE_SAMPLE_MESSAGES)
    message = message_template.format(order_id=order_id)
    
    return {
        "platform": "shopee",
        "platform_conversation_id": f"shopee_conv_{customer_id}",
        "customer_id": customer_id,
        "customer_name": customer_name,
        "content": message,
        "message_id": f"shopee_msg_{random.randint(100000, 999999)}"
    }


async def send_shopee_message(recipient_id: str, message_text: str) -> bool:
    """Mock gửi tin nhắn Shopee"""
    print(f"[Shopee Mock] Send to {recipient_id}: {message_text[:50]}...")
    return True
