from fastapi import APIRouter, Request, Query, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.services.message_service import process_incoming_message
from app.models.models import ShopIntegration, PlatformEnum
import httpx
import time
import hmac
import hashlib
from app.adapters.facebook_adapter import parse_facebook_webhook, verify_facebook_signature
from app.adapters.instagram_adapter import parse_instagram_webhook
from app.adapters.shopee_adapter import generate_mock_shopee_message
from app.adapters.tiktok_adapter import generate_mock_tiktok_message

router = APIRouter()


# ─── Facebook & Instagram Webhook ────────────────────────────────────────────

from fastapi import APIRouter, Request, Query, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.orm import Session

# ... later ...

@router.get("/facebook")
async def facebook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge")
):
    """Xác minh Facebook webhook"""
    if hub_mode == "subscribe" and hub_token == settings.FACEBOOK_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/facebook")
async def facebook_webhook(request: Request, db: Session = Depends(get_db)):
    """Nhận tin nhắn từ Facebook Messenger"""
    body = await request.json()
    
    messages = parse_facebook_webhook(body)
    for msg in messages:
        await process_incoming_message(
            platform=msg["platform"],
            platform_conversation_id=msg["platform_conversation_id"],
            customer_id=msg["customer_id"],
            customer_name=msg["customer_name"],
            message_content=msg["content"],
            db=db
        )
    
    return {"status": "ok"}


@router.get("/instagram")
async def instagram_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge")
):
    """Xác minh Instagram webhook"""
    if hub_mode == "subscribe" and hub_token == settings.FACEBOOK_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/instagram")
async def instagram_webhook(request: Request, db: Session = Depends(get_db)):
    """Nhận tin nhắn từ Instagram DM"""
    body = await request.json()
    
    messages = parse_instagram_webhook(body)
    for msg in messages:
        await process_incoming_message(
            platform=msg["platform"],
            platform_conversation_id=msg["platform_conversation_id"],
            customer_id=msg["customer_id"],
            customer_name=msg["customer_name"],
            message_content=msg["content"],
            db=db
        )
    
    return {"status": "ok"}


# ─── Shopee & TikTok (Mock endpoints) ────────────────────────────────────────

@router.get("/api/auth/shopee/callback")
async def shopee_oauth_callback(code: str, shop_id: str, request: Request, db: Session = Depends(get_db)):
    """Xử lý xác thực OAuth từ Shopee"""
    if not code or not shop_id:
        return {"error": "Missing code or shop_id"}
        
    from app.adapters.shopee_adapter import generate_shopee_signature
    api_path = "/api/v2/auth/token/get"
    sign, timestamp = generate_shopee_signature(api_path)
    
    url = (
        f"https://partner.shopeemobile.com{api_path}?"
        f"partner_id={settings.SHOPEE_PARTNER_ID}&"
        f"timestamp={timestamp}&"
        f"sign={sign}"
    )
    
    partner_id_int = int(settings.SHOPEE_PARTNER_ID) if settings.SHOPEE_PARTNER_ID else 0
    payload = {
        "code": code,
        "shop_id": int(shop_id),
        "partner_id": partner_id_int
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        data = response.json()
        
    if data.get("error"):
        return {"error": "Failed to get access token", "details": data}
        
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    
    # Save to Database
    shop_integration = ShopIntegration(
        shop_id=str(shop_id),
        platform=PlatformEnum.SHOPEE,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=int(time.time()) + data.get("expire_in", 0),
    )
    db.add(shop_integration)
    db.commit()
    
    return {"status": "Success! You can now close this tab."}

from fastapi.responses import RedirectResponse

@router.get("/shopee/login")
async def shopee_login():
    """Tự động sinh link ủy quyền và chuyển hướng người dùng sang Shopee"""
    partner_id = settings.SHOPEE_PARTNER_ID
    partner_key = settings.SHOPEE_PARTNER_KEY
    
    if not partner_id or not partner_key:
        return {"error": "Chưa cài đặt SHOPEE_PARTNER_ID hoặc SHOPEE_PARTNER_KEY trên Railway"}
        
    api_path = "/api/v2/shop/auth_partner"
    timestamp = int(time.time())
    
    base_string = f"{partner_id}{api_path}{timestamp}"
    sign = hmac.new(
        partner_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    redirect_url = "https://silence-backend-v2-production.up.railway.app/webhook/api/auth/shopee/callback"
    auth_url = (
        f"https://partner.test-stable.shopeemobile.com{api_path}?"
        f"partner_id={partner_id}&timestamp={timestamp}&sign={sign}&redirect={redirect_url}"
    )
    
    return RedirectResponse(url=auth_url)

@router.post("/shopee/webhook")
async def shopee_real_webhook(request: Request, db: Session = Depends(get_db)):
    """Nhận Webhook từ Shopee (tin nhắn mới, cập nhật đơn hàng...)"""
    body = await request.json()
    
    from app.adapters.shopee_adapter import parse_shopee_webhook
    messages = parse_shopee_webhook(body)
    
    for msg in messages:
        await process_incoming_message(
            platform=msg["platform"],
            platform_conversation_id=msg["platform_conversation_id"],
            customer_id=msg["customer_id"],
            customer_name=msg["customer_name"],
            message_content=msg["content"],
            db=db
        )
        
    # Shopee requires a specific response format for Push Mechanism
    return {"code": 0, "msg": "success"}

@router.post("/shopee/mock")
async def shopee_mock_message(db: Session = Depends(get_db)):
    """Tạo tin nhắn mock từ Shopee (để test)"""
    from app.adapters.shopee_adapter import generate_mock_shopee_message
    msg = generate_mock_shopee_message()
    result = await process_incoming_message(
        platform=msg["platform"],
        platform_conversation_id=msg["platform_conversation_id"],
        customer_id=msg["customer_id"],
        customer_name=msg["customer_name"],
        message_content=msg["content"],
        db=db
    )
    return {"status": "ok", "data": msg, "result": result}


@router.get("/api/auth/tiktok/callback")
async def tiktok_oauth_callback(code: str, request: Request, db: Session = Depends(get_db)):
    """Xử lý xác thực OAuth từ TikTok Shop"""
    if not code:
        return {"error": "Missing authorization code"}
        
    url = (
        f"https://auth.tiktok-shops.com/api/v2/token/get?"
        f"app_key={settings.TIKTOK_APP_KEY}&"
        f"app_secret={settings.TIKTOK_APP_SECRET}&"
        f"auth_code={code}&"
        f"grant_type=authorized_code"
    )
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        
    if data.get("code") != 0:
        return {"error": "Failed to get access token", "details": data}
        
    token_data = data.get("data", {})
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    
    # Save to Database
    shop_integration = ShopIntegration(
        shop_id=f"tiktok_{int(time.time())}", # Temporary ID until we fetch actual shop details
        platform=PlatformEnum.TIKTOK,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    db.add(shop_integration)
    db.commit()
    
    # Trả về mã HTML báo thành công cho trình duyệt
    return {"status": "Success! You can now close this tab."}

@router.post("/tiktok/webhook")
async def tiktok_real_webhook(request: Request, db: Session = Depends(get_db)):
    """Nhận Webhook từ TikTok (tin nhắn mới, cập nhật đơn hàng...)"""
    body = await request.json()
    
    # Tạm thời chỉ lấy type để log
    msg_type = body.get("type")
    
    # Pass to adapter to process message
    from app.adapters.tiktok_adapter import parse_tiktok_webhook
    messages = parse_tiktok_webhook(body)
    
    for msg in messages:
        await process_incoming_message(
            platform=msg["platform"],
            platform_conversation_id=msg["platform_conversation_id"],
            customer_id=msg["customer_id"],
            customer_name=msg["customer_name"],
            message_content=msg["content"],
            db=db
        )
        
    return {"code": 0, "msg": "success"}

@router.post("/tiktok/mock")
async def tiktok_mock_message(db: Session = Depends(get_db)):
    """Tạo tin nhắn mock từ TikTok (để test)"""
    from app.adapters.tiktok_adapter import generate_mock_tiktok_message
    msg = generate_mock_tiktok_message()
    result = await process_incoming_message(
        platform=msg["platform"],
        platform_conversation_id=msg["platform_conversation_id"],
        customer_id=msg["customer_id"],
        customer_name=msg["customer_name"],
        message_content=msg["content"],
        db=db
    )
    return {"status": "ok", "data": msg, "result": result}


@router.post("/simulate")
async def simulate_all_platforms(db: Session = Depends(get_db)):
    """Tạo tin nhắn mock từ tất cả platforms cùng lúc (để demo)"""
    results = []
    for mock_fn in [generate_mock_shopee_message, generate_mock_tiktok_message]:
        msg = mock_fn()
        result = await process_incoming_message(
            platform=msg["platform"],
            platform_conversation_id=msg["platform_conversation_id"],
            customer_id=msg["customer_id"],
            customer_name=msg["customer_name"],
            message_content=msg["content"],
            db=db
        )
        results.append(result)
    return {"status": "ok", "simulated": len(results)}
