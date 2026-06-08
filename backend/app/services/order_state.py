"""
Order State Manager — Quản lý trạng thái đặt hàng trong chat.
Theo dõi quá trình thu thập thông tin đơn hàng từ khách qua chat.
"""
import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Trạng thái đơn hàng trong chat
ORDER_STATES = {
    "IDLE": "idle",                       # Chưa có order flow
    "COLLECTING_PRODUCT": "collecting_product",  # Đang xác định sản phẩm
    "COLLECTING_INFO": "collecting_info",  # Đang thu thập thông tin khách
    "CONFIRMING": "confirming",            # Chờ khách xác nhận
    "CREATING": "creating",               # Đang tạo đơn
    "DONE": "done",                        # Đã tạo xong
    "CANCELLED": "cancelled"              # Khách hủy
}

# In-memory storage cho order states (conversation_id → order_state)
_order_states: Dict[str, Dict[str, Any]] = {}

# Timeout: hủy order flow sau 15 phút không hoạt động
ORDER_TIMEOUT_MINUTES = 15


def _new_order_state() -> Dict[str, Any]:
    """Tạo order state mới."""
    return {
        "state": ORDER_STATES["IDLE"],
        "product_name": None,
        "product_id": None,
        "product_price": None,
        "product_sku": None,
        "size": None,
        "quantity": 1,
        "customer_name": None,
        "customer_phone": None,
        "address": None,
        "note": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


def get_order_state(conversation_id: str) -> Dict[str, Any]:
    """Lấy order state cho conversation, tạo mới nếu chưa có."""
    if conversation_id not in _order_states:
        _order_states[conversation_id] = _new_order_state()
    
    state = _order_states[conversation_id]
    
    # Check timeout
    if state["state"] not in [ORDER_STATES["IDLE"], ORDER_STATES["DONE"], ORDER_STATES["CANCELLED"]]:
        elapsed = datetime.utcnow() - state["updated_at"]
        if elapsed > timedelta(minutes=ORDER_TIMEOUT_MINUTES):
            logger.info(f"[Order] Timeout for conversation {conversation_id}")
            state["state"] = ORDER_STATES["IDLE"]
    
    return state


def start_order_flow(conversation_id: str, product_name: str = None, size: str = None, quantity: int = 1) -> Dict[str, Any]:
    """Bắt đầu order flow cho conversation."""
    state = _new_order_state()
    state["state"] = ORDER_STATES["COLLECTING_PRODUCT"] if not product_name else ORDER_STATES["COLLECTING_INFO"]
    state["product_name"] = product_name
    state["size"] = size
    state["quantity"] = quantity
    _order_states[conversation_id] = state
    logger.info(f"[Order] Started order flow for {conversation_id}: product={product_name}, size={size}")
    return state


def update_order_state(conversation_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Cập nhật thông tin order state."""
    state = get_order_state(conversation_id)
    for key, value in updates.items():
        if key in state and value is not None:
            state[key] = value
    state["updated_at"] = datetime.utcnow()
    _order_states[conversation_id] = state
    return state


def cancel_order_flow(conversation_id: str):
    """Hủy order flow."""
    if conversation_id in _order_states:
        _order_states[conversation_id]["state"] = ORDER_STATES["CANCELLED"]


def complete_order_flow(conversation_id: str):
    """Đánh dấu order flow hoàn tất."""
    if conversation_id in _order_states:
        _order_states[conversation_id]["state"] = ORDER_STATES["DONE"]


def is_in_order_flow(conversation_id: str) -> bool:
    """Kiểm tra conversation có đang trong order flow không."""
    state = get_order_state(conversation_id)
    return state["state"] not in [ORDER_STATES["IDLE"], ORDER_STATES["DONE"], ORDER_STATES["CANCELLED"]]


def get_missing_fields(conversation_id: str) -> List[str]:
    """Trả về danh sách các field còn thiếu."""
    state = get_order_state(conversation_id)
    missing = []
    
    if not state["product_name"]:
        missing.append("product_name")
    if not state["size"]:
        missing.append("size")
    if not state["customer_name"]:
        missing.append("customer_name")
    if not state["customer_phone"]:
        missing.append("customer_phone")
    if not state["address"]:
        missing.append("address")
    
    return missing


def format_order_summary(conversation_id: str) -> str:
    """Tạo bản tóm tắt đơn hàng cho khách xác nhận."""
    state = get_order_state(conversation_id)
    
    price = state.get("product_price", 0)
    qty = state.get("quantity", 1)
    total = (price or 0) * qty
    
    summary = f"""📋 XÁC NHẬN ĐƠN HÀNG:

🛍️ Sản phẩm: {state.get('product_name', 'N/A')}
📏 Size: {state.get('size', 'N/A')}
🔢 Số lượng: {qty}
💰 Giá: {price:,}₫ x {qty} = {total:,}₫

👤 Người nhận: {state.get('customer_name', 'N/A')}
📱 SĐT: {state.get('customer_phone', 'N/A')}
📍 Địa chỉ: {state.get('address', 'N/A')}"""

    if state.get("note"):
        summary += f"\n📝 Ghi chú: {state['note']}"
    
    summary += "\n\nAnh/chị xác nhận đặt hàng không ạ? (Đồng ý / Không)"
    
    return summary


# ─── Parse thông tin từ tin nhắn khách ─────────────────────────────

def parse_order_intent(message: str) -> Dict[str, Any]:
    """
    Parse thông tin đặt hàng từ tin nhắn khách.
    Returns: {"wants_order": bool, "product_name": str, "size": str, "quantity": int}
    """
    msg_lower = message.lower()
    
    # Detect intent mua hàng
    order_keywords = [
        "mua", "đặt hàng", "đặt đơn", "order", "đặt", "mua ngay", 
        "lấy", "chốt đơn", "chốt", "mình lấy", "em lấy", "anh lấy",
        "tôi mua", "muốn mua", "đặt mua", "mua luôn", "lấy luôn",
        "cho mình", "cho em", "cho anh", "gửi cho"
    ]
    
    wants_order = any(kw in msg_lower for kw in order_keywords)
    if not wants_order:
        return {"wants_order": False}
    
    result = {"wants_order": True, "product_name": None, "size": None, "quantity": 1}
    
    # Extract size
    size_patterns = [
        r'\bsize\s*([SMLX]{1,3})\b',
        r'\b(XXL|XL|XS|S|M|L)\b',
        r'\bcỡ\s*([SMLX]{1,3})\b',
    ]
    for pattern in size_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            result["size"] = match.group(1).upper()
            break
    
    # Extract quantity
    qty_patterns = [
        r'(\d+)\s*(?:cái|chiếc|bộ|đôi|sản phẩm|sp)',
        r'(?:mua|lấy|đặt)\s*(\d+)',
    ]
    for pattern in qty_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            qty = int(match.group(1))
            if 1 <= qty <= 99:
                result["quantity"] = qty
            break
    
    # Extract product name (phần còn lại sau khi bỏ keywords)
    product_name = message
    for kw in order_keywords:
        product_name = product_name.lower().replace(kw, "")
    # Bỏ size và quantity khỏi product name
    product_name = re.sub(r'\bsize\s*[SMLX]{1,3}\b', '', product_name, flags=re.IGNORECASE)
    product_name = re.sub(r'\b(XXL|XL|XS)\b', '', product_name, flags=re.IGNORECASE)
    product_name = re.sub(r'\d+\s*(?:cái|chiếc|bộ)', '', product_name)
    product_name = re.sub(r'\s+', ' ', product_name).strip().strip(',').strip('.')
    
    if len(product_name) >= 2:
        result["product_name"] = product_name
    
    return result


def parse_customer_info(message: str) -> Dict[str, Any]:
    """
    Parse thông tin khách hàng từ tin nhắn.
    Hỗ trợ các format:
    - "Nguyễn Văn A, 0912345678, 123 Nguyễn Huệ Q1"
    - Từng dòng riêng lẻ
    """
    info = {}
    msg = message.strip()
    
    # Extract phone number
    phone_match = re.search(r'(0[0-9]{9,10})', msg)
    if phone_match:
        info["customer_phone"] = phone_match.group(1)
    
    # Extract size nếu có
    size_match = re.search(r'\bsize\s*([SMLX]{1,3})\b', msg, re.IGNORECASE)
    if not size_match:
        size_match = re.search(r'\b(XXL|XL|XS|S|M|L)\b', msg)
    if size_match:
        info["size"] = size_match.group(1).upper()
    
    # Nếu có dấu phẩy → tách theo phẩy
    parts = [p.strip() for p in msg.split(',') if p.strip()]
    
    if len(parts) >= 2:
        for part in parts:
            part_clean = part.strip()
            # Phone đã extract ở trên
            if re.match(r'^0[0-9]{9,10}$', part_clean):
                continue
            # Nếu chứa số nhà/đường/quận/phường → address
            elif any(kw in part_clean.lower() for kw in ['đường', 'phường', 'quận', 'huyện', 'tp', 'tỉnh', 'số', 'ngõ', 'hẻm', 'thôn', 'xã']):
                info["address"] = part_clean
            # Nếu ngắn và không có số → có thể là tên
            elif len(part_clean) <= 50 and not re.search(r'\d{3,}', part_clean) and "customer_name" not in info:
                info["customer_name"] = part_clean
            # Còn lại có thể là address
            elif "address" not in info and len(part_clean) > 5:
                info["address"] = part_clean
    else:
        # Nếu không có phẩy, kiểm tra xem là tên, phone, hay address
        clean = msg
        if phone_match:
            clean = clean.replace(phone_match.group(1), "").strip()
        if size_match:
            clean = re.sub(r'\bsize\s*[SMLX]{1,3}\b', '', clean, flags=re.IGNORECASE).strip()
        
        if clean:
            # Nếu ngắn và chỉ chữ → tên
            if len(clean) <= 30 and not re.search(r'\d', clean) and not any(kw in clean.lower() for kw in ['đường', 'phường', 'quận']):
                info["customer_name"] = clean
            # Nếu có từ khóa địa chỉ → address
            elif any(kw in clean.lower() for kw in ['đường', 'phường', 'quận', 'huyện', 'tp', 'số', 'ngõ', 'hẻm']):
                info["address"] = clean
    
    return info


def parse_confirmation(message: str) -> Optional[bool]:
    """Parse xem khách đồng ý hay hủy đơn."""
    msg_lower = message.lower().strip()
    
    yes_words = ["đồng ý", "ok", "được", "oke", "yes", "có", "xác nhận", "đặt", "chốt", "ừ", "uh", "đúng", "đặt luôn", "ok luôn", "oki"]
    no_words = ["không", "hủy", "thôi", "cancel", "no", "bỏ", "dừng", "ko", "hông", "k"]
    
    if any(w in msg_lower for w in yes_words):
        return True
    if any(w in msg_lower for w in no_words):
        return False
    
    return None  # Không xác định


def get_prompt_for_missing(missing_fields: List[str]) -> str:
    """Tạo câu hỏi cho các field còn thiếu."""
    prompts = {
        "product_name": "Anh/chị muốn mua sản phẩm nào ạ?",
        "size": "Anh/chị chọn size gì ạ? (S/M/L/XL/XXL)",
        "customer_name": "Cho em xin tên người nhận hàng nhé ạ",
        "customer_phone": "Số điện thoại nhận hàng của anh/chị là gì ạ?",
        "address": "Địa chỉ giao hàng cụ thể (số nhà, đường, quận/huyện, tỉnh/TP) ạ?"
    }
    
    if not missing_fields:
        return ""
    
    # Hỏi nhiều field cùng lúc nếu thiếu 2-3
    if len(missing_fields) <= 3 and set(missing_fields) == {"customer_name", "customer_phone", "address"}:
        return "Dạ, để tạo đơn hàng, anh/chị cho em xin:\n- Họ tên người nhận\n- Số điện thoại\n- Địa chỉ giao hàng\n\n(Có thể gửi 1 tin nhắn, cách nhau bằng dấu phẩy ạ)"
    
    if len(missing_fields) == 2 and "customer_name" in missing_fields and "customer_phone" in missing_fields:
        return "Dạ, anh/chị cho em xin họ tên và số điện thoại nhận hàng nhé ạ"
    
    # Hỏi từng field
    return prompts.get(missing_fields[0], "Anh/chị vui lòng cung cấp thêm thông tin nhé ạ")
