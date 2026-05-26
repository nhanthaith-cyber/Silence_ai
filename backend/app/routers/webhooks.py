from fastapi import APIRouter, Request, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.services.message_service import process_incoming_message
from app.adapters.facebook_adapter import parse_facebook_webhook, verify_facebook_signature
from app.adapters.instagram_adapter import parse_instagram_webhook
from app.adapters.shopee_adapter import generate_mock_shopee_message
from app.adapters.tiktok_adapter import generate_mock_tiktok_message

router = APIRouter()


# ─── Facebook & Instagram Webhook ────────────────────────────────────────────

@router.get("/facebook")
async def facebook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge")
):
    """Xác minh Facebook webhook"""
    if hub_mode == "subscribe" and hub_token == settings.FACEBOOK_VERIFY_TOKEN:
        return int(hub_challenge)
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
        return int(hub_challenge)
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

@router.post("/shopee/mock")
async def shopee_mock_message(db: Session = Depends(get_db)):
    """Tạo tin nhắn mock từ Shopee (để test)"""
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


@router.post("/tiktok/mock")
async def tiktok_mock_message(db: Session = Depends(get_db)):
    """Tạo tin nhắn mock từ TikTok (để test)"""
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
