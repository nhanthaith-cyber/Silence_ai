"""
Shopee Adapter — Tích hợp thật với Shopee Open Platform V2 API
Bao gồm: OAuth token refresh, đơn hàng, sản phẩm, tồn kho, chat
"""
import random
import hmac
import hashlib
import time
import httpx
from datetime import datetime
from typing import Optional
from app.core.config import settings


# ─── Signature Generation ─────────────────────────────────────────────────────

def generate_shopee_signature(api_path: str, params: dict = None) -> tuple:
    """Tạo chữ ký HMAC-SHA256 theo chuẩn Shopee Open Platform"""
    partner_id = str(settings.SHOPEE_PARTNER_ID).strip() if settings.SHOPEE_PARTNER_ID else ""
    partner_key = str(settings.SHOPEE_PARTNER_KEY).strip() if settings.SHOPEE_PARTNER_KEY else ""
    timestamp = int(time.time())
    
    # Base string: partner_id + api_path + timestamp + access_token(if any) + shop_id(if any)
    base_string = f"{int(partner_id)}{api_path}{timestamp}"
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


# ─── Shopee API Client ────────────────────────────────────────────────────────

class ShopeeAPIClient:
    """Client chính để gọi mọi Shopee API — tự quản lý token refresh."""
    
    def __init__(self):
        self.base_url = settings.SHOPEE_API_BASE_URL
        self.partner_id = int(str(settings.SHOPEE_PARTNER_ID).strip()) if settings.SHOPEE_PARTNER_ID else 0
        self.partner_key = str(settings.SHOPEE_PARTNER_KEY).strip() if settings.SHOPEE_PARTNER_KEY else ""
    
    def _sign(self, api_path: str, access_token: str = None, shop_id: int = None) -> tuple:
        """Tạo chữ ký cho API request"""
        timestamp = int(time.time())
        base_string = f"{self.partner_id}{api_path}{timestamp}"
        if access_token:
            base_string += access_token
        if shop_id:
            base_string += str(shop_id)
        
        sign = hmac.new(
            self.partner_key.encode('utf-8'),
            base_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return sign, timestamp
    
    async def refresh_access_token(self, shop_id: int, refresh_token: str) -> dict:
        """Refresh access_token khi hết hạn (4 giờ)"""
        api_path = "/api/v2/auth/access_token/get"
        sign, timestamp = self._sign(api_path)
        
        url = (
            f"{self.base_url}{api_path}"
            f"?partner_id={self.partner_id}"
            f"&timestamp={timestamp}"
            f"&sign={sign}"
        )
        
        payload = {
            "shop_id": shop_id,
            "refresh_token": refresh_token,
            "partner_id": self.partner_id,
        }
        
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
        
        if data.get("error"):
            print(f"[Shopee] Token refresh failed: {data}")
            return None
        
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expire_in": data.get("expire_in", 14400),  # 4 giờ
        }
    
    async def get_valid_token(self, db) -> dict:
        """Lấy token hợp lệ — tự refresh nếu hết hạn.
        Returns: {"access_token": str, "shop_id": int} hoặc None
        """
        from app.models.models import ShopIntegration, PlatformEnum
        
        shop = db.query(ShopIntegration).filter(
            ShopIntegration.platform == PlatformEnum.SHOPEE,
            ShopIntegration.is_active == True
        ).first()
        
        if not shop:
            print("[Shopee] No active shop integration found")
            return None
        
        now = int(time.time())
        
        # Token còn hạn (trừ 5 phút buffer)
        if shop.expires_at and now < (shop.expires_at - 300):
            return {
                "access_token": shop.access_token,
                "shop_id": int(shop.shop_id),
            }
        
        # Token hết hạn → refresh
        print(f"[Shopee] Token expired for shop {shop.shop_id}, refreshing...")
        result = await self.refresh_access_token(
            shop_id=int(shop.shop_id),
            refresh_token=shop.refresh_token
        )
        
        if not result:
            return None
        
        # Cập nhật DB
        shop.access_token = result["access_token"]
        shop.refresh_token = result["refresh_token"]
        shop.expires_at = now + result["expire_in"]
        db.commit()
        
        print(f"[Shopee] Token refreshed for shop {shop.shop_id}")
        return {
            "access_token": result["access_token"],
            "shop_id": int(shop.shop_id),
        }
    
    async def _api_request(self, method: str, api_path: str, db,
                           params: dict = None, payload: dict = None) -> dict:
        """Gọi Shopee API với tự động sign + token"""
        token_info = await self.get_valid_token(db)
        if not token_info:
            return {"error": "no_token", "message": "Chưa kết nối shop Shopee"}
        
        access_token = token_info["access_token"]
        shop_id = token_info["shop_id"]
        sign, timestamp = self._sign(api_path, access_token=access_token, shop_id=shop_id)
        
        url = (
            f"{self.base_url}{api_path}"
            f"?partner_id={self.partner_id}"
            f"&timestamp={timestamp}"
            f"&sign={sign}"
            f"&access_token={access_token}"
            f"&shop_id={shop_id}"
        )
        
        # Thêm params vào URL
        if params:
            for k, v in params.items():
                url += f"&{k}={v}"
        
        async with httpx.AsyncClient(timeout=15) as client:
            if method == "GET":
                resp = await client.get(url)
            else:
                resp = await client.post(url, json=payload or {})
            
            return resp.json()
    
    # ─── Order APIs ────────────────────────────────────────────────────────
    
    async def get_order_list(self, db, time_range_field: str = "create_time",
                             page_size: int = 20, cursor: str = "") -> dict:
        """Lấy danh sách đơn hàng"""
        now = int(time.time())
        params = {
            "time_range_field": time_range_field,
            "time_from": now - (30 * 86400),  # 30 ngày gần nhất
            "time_to": now,
            "page_size": page_size,
            "order_status": "ALL",
        }
        if cursor:
            params["cursor"] = cursor
        
        return await self._api_request("GET", "/api/v2/order/get_order_list", db, params=params)
    
    async def get_order_detail(self, db, order_sn_list: list) -> dict:
        """Lấy chi tiết đơn hàng"""
        params = {
            "order_sn_list": ",".join(order_sn_list),
            "response_optional_fields": "buyer_user_id,buyer_username,item_list,pay_time,shipping_carrier,order_status"
        }
        return await self._api_request("GET", "/api/v2/order/get_order_detail", db, params=params)
    
    # ─── Product APIs ──────────────────────────────────────────────────────
    
    async def get_product_list(self, db, offset: int = 0, page_size: int = 50) -> dict:
        """Lấy danh sách sản phẩm"""
        params = {
            "offset": offset,
            "page_size": page_size,
            "item_status": "NORMAL",
        }
        return await self._api_request("GET", "/api/v2/product/get_item_list", db, params=params)
    
    async def get_product_detail(self, db, item_id_list: list) -> dict:
        """Lấy chi tiết sản phẩm"""
        params = {
            "item_id_list": ",".join(str(i) for i in item_id_list),
        }
        return await self._api_request("GET", "/api/v2/product/get_item_base_info", db, params=params)
    
    async def get_model_list(self, db, item_id: int) -> dict:
        """Lấy danh sách biến thể (model) — bao gồm tồn kho theo size/màu"""
        params = {"item_id": item_id}
        return await self._api_request("GET", "/api/v2/product/get_model_list", db, params=params)
    
    # ─── Chat APIs ─────────────────────────────────────────────────────────
    
    async def send_message(self, db, conversation_id: str, message: str) -> dict:
        """Gửi tin nhắn cho khách qua Shopee Chat"""
        token_info = await self.get_valid_token(db)
        if not token_info:
            return {"error": "no_token"}
        
        payload = {
            "to_id": int(conversation_id),
            "message_type": "text",
            "content": {"text": message},
        }
        return await self._api_request("POST", "/api/v2/sellerchat/send_message", db, payload=payload)
    
    async def get_conversations(self, db, direction: str = "latest", page_size: int = 25) -> dict:
        """Lấy danh sách cuộc hội thoại"""
        params = {
            "direction": direction,
            "type": "all",
            "page_size": page_size,
        }
        return await self._api_request("GET", "/api/v2/sellerchat/get_conversation_list", db, params=params)
    
    async def get_messages(self, db, conversation_id: str, page_size: int = 25) -> dict:
        """Lấy tin nhắn trong cuộc hội thoại"""
        params = {
            "conversation_id": conversation_id,
            "page_size": page_size,
            "direction": "latest",
        }
        return await self._api_request("GET", "/api/v2/sellerchat/get_message", db, params=params)


# ─── Global Client Instance ───────────────────────────────────────────────────

shopee_client = ShopeeAPIClient()


# ─── Webhook Parsing ──────────────────────────────────────────────────────────

def parse_shopee_webhook(payload: dict) -> list:
    """Phân tích payload từ Shopee Open Platform Push Mechanism"""
    messages = []
    
    code = payload.get("code")
    # Code 3 = Shopee Chat Push
    if code == 3:
        data = payload.get("data", {})
        
        # Type "message" = tin nhắn mới
        msg_type = data.get("type")
        if msg_type == "message":
            content = data.get("content", {})
            sender_id = str(content.get("from_id", "unknown"))
            shop_id = str(data.get("shop_id", payload.get("shop_id", "")))
            
            # Bỏ qua tin nhắn từ chính shop
            if sender_id == shop_id:
                return messages
            
            text = ""
            msg_content_type = content.get("message_type", "")
            if msg_content_type == "text":
                text = content.get("content", {}).get("text", "")
            elif msg_content_type == "image":
                text = "[Hình ảnh]"
            elif msg_content_type == "sticker":
                text = "[Sticker]"
            else:
                text = f"[{msg_content_type}]"
            
            if text:
                messages.append({
                    "platform": "shopee",
                    "platform_conversation_id": f"shopee_{content.get('conversation_id', sender_id)}",
                    "customer_id": sender_id,
                    "customer_name": content.get("from_user_name", f"Shopee_{sender_id[-4:]}"),
                    "content": text,
                    "message_id": str(content.get("message_id", f"msg_{random.randint(1000, 9999)}"))
                })
    
    return messages


def verify_shopee_push_signature(body: bytes, authorization: str) -> bool:
    """Xác thực Push signature từ Shopee"""
    partner_key = str(settings.SHOPEE_PARTNER_KEY).strip()
    
    # Shopee Push: Authorization = base_string gồm url + body, hash bằng partner_key
    expected = hmac.new(
        partner_key.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, authorization)


# ─── Send Message (thật) ──────────────────────────────────────────────────────

async def send_shopee_message(recipient_id: str, message_text: str, db=None) -> bool:
    """Gửi tin nhắn Shopee — dùng API thật nếu có DB, mock nếu không"""
    if db:
        result = await shopee_client.send_message(db, recipient_id, message_text)
        if result.get("error"):
            print(f"[Shopee] Send message failed: {result}")
            return False
        return True
    else:
        print(f"[Shopee Mock] Send to {recipient_id}: {message_text[:50]}...")
        return True


# ─── Mock Data (giữ lại để test) ──────────────────────────────────────────────

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
