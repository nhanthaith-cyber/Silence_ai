"""
Shopee API Router — REST endpoints để Frontend và AI truy vấn dữ liệu Shopee
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.adapters.shopee_adapter import shopee_client

router = APIRouter(prefix="/api/shopee", tags=["Shopee API"])


@router.get("/status")
async def shopee_status(db: Session = Depends(get_db)):
    """Kiểm tra trạng thái kết nối Shopee"""
    token_info = await shopee_client.get_valid_token(db)
    if token_info:
        return {
            "connected": True,
            "shop_id": token_info["shop_id"],
            "token_valid": True,
        }
    return {"connected": False, "token_valid": False}


@router.get("/orders")
async def get_orders(
    page_size: int = Query(20, le=50),
    cursor: str = Query(""),
    db: Session = Depends(get_db)
):
    """Lấy danh sách đơn hàng 30 ngày gần nhất"""
    return await shopee_client.get_order_list(db, page_size=page_size, cursor=cursor)


@router.get("/orders/{order_sn}")
async def get_order_detail(order_sn: str, db: Session = Depends(get_db)):
    """Lấy chi tiết 1 đơn hàng"""
    return await shopee_client.get_order_detail(db, order_sn_list=[order_sn])


@router.get("/products")
async def get_products(
    offset: int = Query(0, ge=0),
    page_size: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """Lấy danh sách sản phẩm"""
    return await shopee_client.get_product_list(db, offset=offset, page_size=page_size)


@router.get("/products/{item_id}")
async def get_product_detail(item_id: int, db: Session = Depends(get_db)):
    """Lấy chi tiết 1 sản phẩm"""
    return await shopee_client.get_product_detail(db, item_id_list=[item_id])


@router.get("/products/{item_id}/stock")
async def get_product_stock(item_id: int, db: Session = Depends(get_db)):
    """Lấy tồn kho theo biến thể (size/màu)"""
    return await shopee_client.get_model_list(db, item_id=item_id)


@router.get("/chat/conversations")
async def get_chat_conversations(
    page_size: int = Query(25, le=100),
    db: Session = Depends(get_db)
):
    """Lấy danh sách cuộc hội thoại chat"""
    return await shopee_client.get_conversations(db, page_size=page_size)


@router.get("/chat/{conversation_id}/messages")
async def get_chat_messages(
    conversation_id: str,
    page_size: int = Query(25, le=100),
    db: Session = Depends(get_db)
):
    """Lấy tin nhắn trong 1 cuộc hội thoại"""
    return await shopee_client.get_messages(db, conversation_id=conversation_id, page_size=page_size)


@router.get("/token/refresh")
async def manual_refresh_token(db: Session = Depends(get_db)):
    """Ép refresh token thủ công (debug)"""
    from app.models.models import ShopIntegration, PlatformEnum
    import time
    
    shop = db.query(ShopIntegration).filter(
        ShopIntegration.platform == PlatformEnum.SHOPEE,
        ShopIntegration.is_active == True
    ).first()
    
    if not shop:
        return {"error": "No shop found"}
    
    result = await shopee_client.refresh_access_token(
        shop_id=int(shop.shop_id),
        refresh_token=shop.refresh_token
    )
    
    if not result:
        return {"error": "Refresh failed"}
    
    shop.access_token = result["access_token"]
    shop.refresh_token = result["refresh_token"]
    shop.expires_at = int(time.time()) + result["expire_in"]
    db.commit()
    
    return {
        "status": "Token refreshed successfully",
        "shop_id": shop.shop_id,
        "expires_in_hours": result["expire_in"] / 3600,
    }
