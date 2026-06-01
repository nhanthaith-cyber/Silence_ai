from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from pydantic import BaseModel

router = APIRouter(prefix="/api/nhanh", tags=["Nhanh.vn API"])

class NhanhConfigUpdate(BaseModel):
    business_id: str
    access_token: str

@router.get("/config")
async def get_nhanh_config(db: Session = Depends(get_db)):
    """Lấy cấu hình Nhanh.vn hiện tại"""
    from app.models.models import ShopIntegration, PlatformEnum
    
    shop = db.query(ShopIntegration).filter(
        ShopIntegration.platform == PlatformEnum.NHANH_VN,
        ShopIntegration.is_active == True
    ).first()
    
    if not shop:
        return {"configured": False}
        
    return {
        "configured": True,
        "business_id": shop.shop_id,
        "access_token": shop.access_token[:5] + "..." + shop.access_token[-5:] if shop.access_token else ""
    }

@router.post("/config")
async def update_nhanh_config(config: NhanhConfigUpdate, db: Session = Depends(get_db)):
    """Cập nhật cấu hình Nhanh.vn"""
    from app.models.models import ShopIntegration, PlatformEnum
    import uuid
    
    shop = db.query(ShopIntegration).filter(
        ShopIntegration.platform == PlatformEnum.NHANH_VN
    ).first()
    
    if shop:
        shop.shop_id = config.business_id
        shop.access_token = config.access_token
        shop.is_active = True
    else:
        new_shop = ShopIntegration(
            id=str(uuid.uuid4()),
            shop_id=config.business_id,
            platform=PlatformEnum.NHANH_VN,
            access_token=config.access_token,
            is_active=True
        )
        db.add(new_shop)
        
    db.commit()
    return {"status": "success", "message": "Cập nhật cấu hình Nhanh.vn thành công"}
