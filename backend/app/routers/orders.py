"""
Orders Router — API endpoint quản lý đơn hàng tạo từ AI Chat
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.order_state import (
    get_order_state, is_in_order_flow, cancel_order_flow, _order_states
)

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.get("/active")
async def get_active_orders():
    """Lấy danh sách đơn hàng đang trong quá trình tạo."""
    active = []
    for conv_id, state in _order_states.items():
        if state["state"] not in ["idle", "done", "cancelled"]:
            active.append({
                "conversation_id": conv_id,
                "state": state["state"],
                "product_name": state.get("product_name"),
                "size": state.get("size"),
                "quantity": state.get("quantity"),
                "customer_name": state.get("customer_name"),
                "customer_phone": state.get("customer_phone"),
                "address": state.get("address"),
                "updated_at": state.get("updated_at", "").isoformat() if state.get("updated_at") else None
            })
    return {"orders": active, "total": len(active)}


@router.get("/history")
async def get_order_history():
    """Lấy lịch sử đơn hàng đã tạo."""
    history = []
    for conv_id, state in _order_states.items():
        if state["state"] in ["done", "cancelled"]:
            history.append({
                "conversation_id": conv_id,
                "state": state["state"],
                "product_name": state.get("product_name"),
                "size": state.get("size"),
                "quantity": state.get("quantity"),
                "customer_name": state.get("customer_name"),
                "customer_phone": state.get("customer_phone"),
                "address": state.get("address"),
                "created_at": state.get("created_at", "").isoformat() if state.get("created_at") else None
            })
    return {"orders": history, "total": len(history)}


@router.get("/{conversation_id}")
async def get_order_by_conversation(conversation_id: str):
    """Lấy thông tin đơn hàng theo conversation ID."""
    if conversation_id not in _order_states:
        return {"found": False, "message": "Không tìm thấy đơn hàng"}
    
    state = _order_states[conversation_id]
    return {
        "found": True,
        "order": {
            "conversation_id": conversation_id,
            "state": state["state"],
            "product_name": state.get("product_name"),
            "product_id": state.get("product_id"),
            "product_sku": state.get("product_sku"),
            "product_price": state.get("product_price"),
            "size": state.get("size"),
            "quantity": state.get("quantity"),
            "customer_name": state.get("customer_name"),
            "customer_phone": state.get("customer_phone"),
            "address": state.get("address"),
            "note": state.get("note"),
            "created_at": state.get("created_at", "").isoformat() if state.get("created_at") else None,
            "updated_at": state.get("updated_at", "").isoformat() if state.get("updated_at") else None
        }
    }


@router.delete("/{conversation_id}")
async def cancel_order(conversation_id: str):
    """Hủy đơn hàng đang tạo."""
    if conversation_id not in _order_states:
        return {"success": False, "message": "Không tìm thấy đơn hàng"}
    
    cancel_order_flow(conversation_id)
    return {"success": True, "message": "Đã hủy đơn hàng"}
