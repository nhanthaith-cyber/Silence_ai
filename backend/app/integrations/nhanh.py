"""
Nhanh.vn Adapter — Giao tiếp API Nhanh.vn (phiên bản V2)
"""
import json
import httpx
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class NhanhVNAdapter:
    def __init__(self, db=None):
        self.app_id = settings.NHANH_APP_ID or "77546"
        self.secret_key = settings.NHANH_SECRET_KEY or "QBjZ2fXGowF53SQo4By6aYapBm5aurxHOW07AGdoubnZomUAr3PQrCEYUK50ex1z60tgcdZpCKh4N5gtlPkODRnvQCiEc6WwyUiPKVsxM5rZcW5r2JMRQe10lW2mN7es"
        self.base_url = "https://open.nhanh.vn/api"
        self.db = db
        
    def _get_token(self) -> Optional[dict]:
        if not self.db:
            return None
        from app.models.models import ShopIntegration, PlatformEnum
        shop = self.db.query(ShopIntegration).filter(
            ShopIntegration.platform == PlatformEnum.NHANH_VN,
            ShopIntegration.is_active == True
        ).first()
        if shop:
            return {
                "business_id": shop.shop_id,
                "access_token": shop.access_token
            }
        return None

    async def _post(self, endpoint: str, data_payload: dict) -> dict:
        token_info = self._get_token()
        if not token_info:
            logger.warning("[Nhanh.vn] No token found in DB.")
            return {"code": 0, "messages": "No token"}
            
        url = f"{self.base_url}{endpoint}"
        
        # Nhanh.vn V2 requires these fields as form-data
        payload = {
            "version": "2.0",
            "appId": self.app_id,
            "businessId": token_info["business_id"],
            "accessToken": token_info["access_token"],
            "data": json.dumps(data_payload)
        }
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(url, data=payload)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"[Nhanh.vn] HTTP {response.status_code}: {response.text}")
                    return {"code": 0, "messages": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"[Nhanh.vn] Error: {e}")
            return {"code": 0, "messages": str(e)}

    async def check_inventory(self, query: str) -> Dict[str, Any]:
        """
        Gọi API Nhanh.vn lấy tồn kho thực tế.
        """
        if not self.db:
            return {"status": "error", "message": "No DB context"}
            
        token_info = self._get_token()
        if not token_info:
            return {"status": "error", "message": "Chưa kết nối Nhanh.vn"}
            
        # Tìm sản phẩm theo keyword
        # Để lấy tồn kho, ta gọi product/search hoặc inventory/product
        # Product search trả về thông tin item kèm inventory (đôi khi phải truyền tham số includeInventory)
        # Nhanh.vn V2 /product/search
        data_payload = {
            "name": query,
            "icpp": 5  # Số lượng kết quả
        }
        
        res = await self._post("/product/search", data_payload)
        
        if res.get("code") == 1:
            products_data = res.get("data", {}).get("products", {})
            # products_data is usually a dict where keys are IDs
            
            parsed_data = []
            if isinstance(products_data, dict):
                items = list(products_data.values())
            elif isinstance(products_data, list):
                items = products_data
            else:
                items = []
                
            for item in items:
                name = item.get("name", "")
                sku = item.get("code", "")
                # Tồn kho thực tế (available) = inventory - defect - holding
                available = item.get("available", 0)
                
                parsed_data.append({
                    "product_name": name,
                    "sku": sku,
                    "available_stock": {"Size/Màu chung": available} 
                    # Note: Nhanh.vn returns product parent/child. If it's a child, the name includes size/color.
                })
                
            return {
                "status": "success",
                "source": "nhanh.vn",
                "data": parsed_data
            }
        else:
            return {
                "status": "error",
                "message": res.get("messages", "Unknown error")
            }

    async def search_product_for_order(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Tìm sản phẩm trên Nhanh.vn theo tên để lấy productId cho tạo đơn.
        Returns: {"id": int, "name": str, "price": int, "sku": str} hoặc None
        """
        data_payload = {
            "name": query,
            "icpp": 5
        }
        
        res = await self._post("/product/search", data_payload)
        
        if res.get("code") == 1:
            products_data = res.get("data", {}).get("products", {})
            if isinstance(products_data, dict):
                items = list(products_data.values())
            elif isinstance(products_data, list):
                items = products_data
            else:
                items = []
            
            # Tìm sản phẩm khớp nhất
            query_lower = query.lower()
            best_match = None
            best_score = 0
            
            for item in items:
                name = item.get("name", "").lower()
                score = 0
                for word in query_lower.split():
                    if len(word) >= 2 and word in name:
                        score += 1
                if score > best_score:
                    best_score = score
                    best_match = item
            
            if not best_match and items:
                best_match = items[0]
            
            if best_match:
                return {
                    "id": best_match.get("idNhanh") or best_match.get("id"),
                    "name": best_match.get("name", ""),
                    "price": best_match.get("price", 0),
                    "sku": best_match.get("code", ""),
                    "available": best_match.get("available", 0)
                }
        
        return None

    async def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tạo đơn hàng trên Nhanh.vn.
        
        order_data format:
        {
            "customer_name": "Nguyễn Văn A",
            "customer_phone": "0912345678",
            "address": "123 Nguyễn Huệ, Q1, TP.HCM",
            "products": [{"id": 123, "quantity": 1, "price": 500000}],
            "note": "Ghi chú"
        }
        """
        if not self.db:
            return {"status": "error", "message": "No DB context"}
        
        token_info = self._get_token()
        if not token_info:
            return {"status": "error", "message": "Chưa kết nối Nhanh.vn"}
        
        # Build Nhanh.vn order payload
        nhanh_payload = {
            "info": {
                "type": 1,  # 1 = đơn hàng bán lẻ
                "description": order_data.get("note", "Đơn từ AI Chat - Silence Agent")
            },
            "customer": {
                "name": order_data["customer_name"],
                "mobile": order_data["customer_phone"]
            },
            "shippingAddress": {
                "name": order_data["customer_name"],
                "mobile": order_data["customer_phone"],
                "address": order_data.get("address", "")
            },
            "products": order_data.get("products", [])
        }
        
        logger.info(f"[Nhanh.vn] Creating order: {nhanh_payload}")
        
        res = await self._post("/order/add", nhanh_payload)
        
        if res.get("code") == 1:
            order_id = res.get("data", {}).get("orderId") or res.get("data", {}).get("id")
            return {
                "status": "success",
                "order_id": order_id,
                "message": f"Đã tạo đơn hàng thành công! Mã đơn: {order_id}",
                "raw_data": res.get("data", {})
            }
        else:
            error_msg = res.get("messages", "Lỗi không xác định")
            if isinstance(error_msg, dict):
                error_msg = str(error_msg)
            logger.error(f"[Nhanh.vn] Order creation failed: {error_msg}")
            return {
                "status": "error",
                "message": f"Không thể tạo đơn: {error_msg}"
            }
