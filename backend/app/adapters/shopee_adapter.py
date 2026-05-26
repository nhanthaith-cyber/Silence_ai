"""
Shopee Adapter (Mock trong MVP)
Shopee Open Platform không có webhook chat công khai,
sử dụng mock data để demo. Tích hợp thật khi có API access.
"""
import random
from datetime import datetime

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
