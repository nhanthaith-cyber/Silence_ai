"""
TikTok Shop Adapter (Mock trong MVP)
TikTok Business API yêu cầu đối tác được phê duyệt.
Sử dụng mock data để demo. Tích hợp thật khi có API access.
"""
import random

TIKTOK_SAMPLE_MESSAGES = [
    "Mình thấy video review sản phẩm này, giá bán bao nhiêu vậy shop?",
    "Shop ship toàn quốc không? Phí ship bao nhiêu?",
    "Sản phẩm có size nào? Mình cao 1m65 nặng 55kg mặc size nào?",
    "Voucher giảm giá mình nhập vào sao không được vậy?",
    "Đơn hàng tiktok shop của mình #{order_id} chưa thấy giao",
    "Thanh toán COD được không shop?",
    "Sản phẩm này có màu khác không ạ?",
    "Mình livestream thấy giá khác, sao lúc order lại khác?",
]

TIKTOK_CUSTOMER_NAMES = [
    "user_tiktoker_88", "beauty_lover_vn", "shopaholics2024",
    "Minh Châu TT", "review_queen_vn", "fashion_holic_2k",
    "Linh Linhh", "thuy_shop_review"
]


def parse_tiktok_webhook(payload: dict) -> list:
    """Phân tích payload từ TikTok Shop Open API v2"""
    messages = []
    
    # Payload TikTok thường có cấu trúc:
    # {
    #   "type": 1,
    #   "shop_id": "...",
    #   "timestamp": 123456789,
    #   "data": { ... }
    # }
    
    # Ở bản thực tế, API v2 Chat Webhook trả về tin nhắn mới trong data
    # (Do tài liệu TikTok cập nhật liên tục, tạm thời parse cấu trúc chung)
    
    event_type = payload.get("type")
    
    if event_type == 1:  # Giả sử type 1 là chat message
        data = payload.get("data", {})
        sender_id = data.get("sender_id", "unknown")
        content = data.get("content", "")
        conversation_id = data.get("conversation_id", f"tt_conv_{sender_id}")
        
        # Chỉ nhận tin nhắn từ Khách (không phải từ bot)
        if data.get("sender_role") == "BUYER":
            messages.append({
                "platform": "tiktok",
                "platform_conversation_id": conversation_id,
                "customer_id": sender_id,
                "customer_name": f"TikTok_{sender_id[-4:]}",
                "content": content,
                "message_id": data.get("message_id", f"msg_{random.randint(1000, 9999)}")
            })
            
    return messages


def generate_mock_tiktok_message() -> dict:
    """Tạo tin nhắn mock từ TikTok"""
    customer_idx = random.randint(0, len(TIKTOK_CUSTOMER_NAMES) - 1)
    customer_name = TIKTOK_CUSTOMER_NAMES[customer_idx]
    customer_id = f"tiktok_user_{2000 + customer_idx}"
    order_id = f"TT{random.randint(10000, 99999)}"
    
    message_template = random.choice(TIKTOK_SAMPLE_MESSAGES)
    message = message_template.format(order_id=order_id)
    
    return {
        "platform": "tiktok",
        "platform_conversation_id": f"tiktok_conv_{customer_id}",
        "customer_id": customer_id,
        "customer_name": customer_name,
        "content": message,
        "message_id": f"tiktok_msg_{random.randint(100000, 999999)}"
    }


async def send_tiktok_message(recipient_id: str, message_text: str) -> bool:
    """Mock gửi tin nhắn TikTok"""
    print(f"[TikTok Mock] Send to {recipient_id}: {message_text[:50]}...")
    return True
