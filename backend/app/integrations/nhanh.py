import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class NhanhVNAdapter:
    def __init__(self, app_id: str, secret_key: str):
        self.app_id = app_id
        self.secret_key = secret_key
        self.base_url = "https://open.nhanh.vn/api"
        # Access token will be set after exchange
        self.access_token: Optional[str] = None
        self.business_id: Optional[str] = None

    async def exchange_access_code(self, access_code: str) -> bool:
        """Đổi accessCode lấy accessToken"""
        # Note: The exact endpoint might vary based on Nhanh.vn API version
        url = f"{self.base_url}/oauth/access_token"
        
        payload = {
            "version": "2.0",
            "appId": self.app_id,
            "secretKey": self.secret_key,
            "accessCode": access_code
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Nhanh.vn thường yêu cầu form-data hoặc JSON tùy endpoint
                response = await client.post(url, data=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 1:
                        self.access_token = data.get("data", {}).get("accessToken")
                        self.business_id = data.get("data", {}).get("businessId")
                        logger.info(f"Successfully exchanged Nhanh.vn token for business {self.business_id}")
                        return True
                    else:
                        logger.error(f"Nhanh.vn token exchange failed: {data.get('messages')}")
                else:
                    logger.error(f"HTTP Error {response.status_code} during token exchange")
        except Exception as e:
            logger.error(f"Error connecting to Nhanh.vn: {str(e)}")
            
        return False

    async def check_inventory(self, query: str) -> Dict[str, Any]:
        """
        Gọi API Nhanh.vn lấy tồn kho. 
        Mock response tạm thời để AI có thể hoạt động trong lúc debug thật.
        """
        # Nếu chưa có token thật, trả về data mock chuẩn theo form Nhanh.vn
        # để AI xử lý tiếp luồng chat.
        if not self.access_token:
            logger.warning("No Nhanh.vn access token available. Returning mock inventory data.")
            
            query_lower = query.lower()
            mock_data = []
            
            if "sơ mi" in query_lower:
                mock_data.append({
                    "product_name": "Áo Sơ Mi Kẻ (Nhanh.vn)",
                    "sku": "SOMI-KE",
                    "available_stock": {
                        "Xanh": {"S": 10, "M": 5, "L": 0},
                        "Đen": {"S": 2, "M": 15, "L": 5}
                    }
                })
            elif "quần" in query_lower:
                mock_data.append({
                    "product_name": "Quần Vải Cao Cấp (Nhanh.vn)",
                    "sku": "QUAN-VAI",
                    "available_stock": {
                        "Đen": {"30": 5, "31": 0, "32": 12},
                        "Xám": {"30": 2, "31": 10, "32": 3}
                    }
                })
            else:
                # Default / Polo
                mock_data.append({
                    "product_name": "Áo Polo Premium (Nhanh.vn)",
                    "sku": "POLO-PREM",
                    "available_stock": {
                        "Đen": {"S": 5, "M": 0, "L": 12},
                        "Trắng": {"S": 2, "M": 10, "L": 0}
                    }
                })
                
            return {
                "status": "success",
                "source": "nhanh.vn (mock)",
                "data": mock_data
            }

        # Luồng gọi API thật (sẽ gọi api/product/search hoặc api/inventory)
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # TODO: Khi xử lý response API thật từ Nhanh.vn, 
        # BẮT BUỘC map trường số lượng với trường "available" (Số lượng có thể bán)
        # KHÔNG dùng trường "inventory" (Tổng tồn kho bao gồm hàng lỗi/đang giữ)
        pass
