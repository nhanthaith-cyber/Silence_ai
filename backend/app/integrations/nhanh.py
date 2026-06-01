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
