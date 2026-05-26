import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import CustomerMemory, gen_uuid


# Thời gian sống của memory (6 tháng)
MEMORY_TTL_DAYS = 180


def get_customer_memory(db: Session, customer_id: str, platform: str = 'all') -> dict | None:
    """Lấy memory của khách hàng. Trả về None nếu chưa có hoặc đã hết hạn."""
    memory = db.query(CustomerMemory).filter(
        CustomerMemory.customer_id == customer_id,
        CustomerMemory.platform == platform
    ).first()

    if not memory:
        return None

    # Kiểm tra hết hạn
    if memory.expires_at and memory.expires_at < datetime.utcnow():
        db.delete(memory)
        db.commit()
        return None

    return memory_to_dict(memory)


def update_customer_memory(db: Session, customer_id: str, platform: str, updates: dict) -> dict:
    """Cập nhật hoặc tạo mới memory cho khách hàng."""
    memory = db.query(CustomerMemory).filter(
        CustomerMemory.customer_id == customer_id,
        CustomerMemory.platform == platform
    ).first()

    if not memory:
        # Tạo mới memory
        memory = CustomerMemory(
            id=gen_uuid(),
            customer_id=customer_id,
            platform=platform,
        )
        db.add(memory)

    # Danh sách các field JSON cần merge thay vì ghi đè
    json_fields = {"preferred_sizes", "body_measurements"}

    for field, value in updates.items():
        if value is None:
            continue
        if not hasattr(memory, field):
            continue

        if field in json_fields:
            # Merge JSON: kết hợp dữ liệu cũ + mới
            try:
                existing = json.loads(getattr(memory, field) or '{}')
            except (json.JSONDecodeError, TypeError):
                existing = {}
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    continue
            existing.update(value)
            setattr(memory, field, json.dumps(existing, ensure_ascii=False))
        else:
            setattr(memory, field, value)

    # Gia hạn TTL
    memory.expires_at = datetime.utcnow() + timedelta(days=MEMORY_TTL_DAYS)
    memory.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(memory)
    return memory_to_dict(memory)


def format_memory_for_prompt(memory: dict) -> str:
    """Format memory thành text để inject vào AI system prompt."""
    if not memory:
        return ""

    lines = ["Thông tin khách hàng (sử dụng tự nhiên, không để lộ hệ thống):"]

    # Size thường mua
    try:
        sizes = json.loads(memory.get("preferred_sizes", "{}") or "{}")
        if sizes:
            size_parts = [f"{v} ({k})" for k, v in sizes.items()]
            lines.append(f"- Size thường mua: {', '.join(size_parts)}")
    except (json.JSONDecodeError, TypeError):
        pass

    # Form yêu thích
    if memory.get("preferred_fit"):
        lines.append(f"- Form yêu thích: {memory['preferred_fit']} fit")

    # Phong cách
    if memory.get("style_preferences"):
        lines.append(f"- Phong cách: {memory['style_preferences']}")

    # Số đo
    try:
        measurements = json.loads(memory.get("body_measurements", "{}") or "{}")
        if measurements:
            parts = []
            if "height" in measurements:
                parts.append(f"{measurements['height']}cm")
            if "weight" in measurements:
                parts.append(f"{measurements['weight']}kg")
            if parts:
                lines.append(f"- Số đo: {' / '.join(parts)}")
    except (json.JSONDecodeError, TypeError):
        pass

    # Lần mua gần nhất
    if memory.get("purchase_history_summary"):
        last_purchase = memory.get("last_purchase_date")
        date_str = ""
        if last_purchase:
            if isinstance(last_purchase, str):
                try:
                    last_purchase = datetime.fromisoformat(last_purchase)
                except ValueError:
                    last_purchase = None
            if isinstance(last_purchase, datetime):
                date_str = f" ({last_purchase.strftime('%d/%m')})"
        lines.append(f"- Lần mua gần nhất: {memory['purchase_history_summary']}{date_str}")

    # Độ nhạy giá
    sensitivity_map = {"low": "thấp", "medium": "trung bình", "high": "cao"}
    if memory.get("price_sensitivity") and memory["price_sensitivity"] != "medium":
        label = sensitivity_map.get(memory["price_sensitivity"], memory["price_sensitivity"])
        lines.append(f"- Nhạy cảm về giá: {label}")

    # Lịch sử khiếu nại
    if memory.get("complaint_history"):
        lines.append(f"- Lịch sử khiếu nại: {memory['complaint_history']}")

    # Phong cách giao tiếp
    comm_map = {"formal": "trang trọng", "casual": "thân thiện", "brief": "ngắn gọn"}
    if memory.get("communication_style") and memory["communication_style"] != "casual":
        label = comm_map.get(memory["communication_style"], memory["communication_style"])
        lines.append(f"- Phong cách giao tiếp: {label}")

    # Ghi chú
    if memory.get("notes"):
        lines.append(f"- Ghi chú: {memory['notes']}")

    # Chỉ trả về nếu có thông tin thực sự (ngoài tiêu đề)
    if len(lines) <= 1:
        return ""

    return "\n".join(lines)


def extract_memory_from_ai_response(ai_response: dict) -> dict | None:
    """Trích xuất memory updates từ AI response (field memory_updates)."""
    if not ai_response or not isinstance(ai_response, dict):
        return None

    memory_updates = ai_response.get("memory_updates")
    if not memory_updates or not isinstance(memory_updates, dict):
        return None

    # Lọc bỏ giá trị rỗng
    filtered = {k: v for k, v in memory_updates.items() if v is not None and v != ""}
    return filtered if filtered else None


def cleanup_expired_memories(db: Session) -> int:
    """Xóa memories đã hết hạn. Chạy periodic."""
    now = datetime.utcnow()
    count = db.query(CustomerMemory).filter(
        CustomerMemory.expires_at != None,  # noqa: E711
        CustomerMemory.expires_at < now
    ).delete(synchronize_session="fetch")
    db.commit()
    return count


def memory_to_dict(memory: CustomerMemory) -> dict:
    """Convert SQLAlchemy model to dict."""
    return {
        "id": memory.id,
        "customer_id": memory.customer_id,
        "platform": memory.platform,
        "preferred_sizes": memory.preferred_sizes,
        "preferred_fit": memory.preferred_fit,
        "style_preferences": memory.style_preferences,
        "purchase_history_summary": memory.purchase_history_summary,
        "last_purchase_date": memory.last_purchase_date.isoformat() if memory.last_purchase_date else None,
        "complaint_history": memory.complaint_history,
        "price_sensitivity": memory.price_sensitivity,
        "satisfaction_score": memory.satisfaction_score,
        "communication_style": memory.communication_style,
        "body_measurements": memory.body_measurements,
        "notes": memory.notes,
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
        "expires_at": memory.expires_at.isoformat() if memory.expires_at else None,
    }
