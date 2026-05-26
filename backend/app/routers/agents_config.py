from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.models.models import AgentConfig
import uuid

router = APIRouter()

DEFAULT_PROMPT = """Bạn là trợ lý chăm sóc khách hàng chuyên nghiệp của shop.
- Luôn trả lời bằng tiếng Việt, thân thiện và lịch sự
- Trả lời ngắn gọn, rõ ràng và hữu ích
- Nếu câu hỏi liên quan đến đơn hàng cụ thể, hãy yêu cầu mã đơn hàng
- Nếu không chắc chắn, hãy nói rõ và đề nghị chuyển nhân viên hỗ trợ
- Sử dụng emoji phù hợp để tạo cảm giác thân thiện
- Kết thúc bằng câu hỏi xem khách có cần hỗ trợ thêm không"""


class AgentConfigCreate(BaseModel):
    name: str = "AI Assistant"
    platform: str = "all"
    system_prompt: str = DEFAULT_PROMPT
    temperature: float = 0.7
    auto_reply: bool = True
    confidence_threshold: float = 0.7
    greeting_message: Optional[str] = "Xin chào! Mình có thể giúp gì cho bạn? 😊"


class AgentConfigUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    auto_reply: Optional[bool] = None
    confidence_threshold: Optional[float] = None
    greeting_message: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_agents(db: Session = Depends(get_db)):
    agents = db.query(AgentConfig).all()
    if not agents:
        # Tạo agent mặc định nếu chưa có
        default = AgentConfig(
            id=str(uuid.uuid4()),
            name="AI Assistant mặc định",
            platform="all",
            system_prompt=DEFAULT_PROMPT,
            temperature=0.7,
            auto_reply=True,
            confidence_threshold=0.7,
            greeting_message="Xin chào! Mình có thể giúp gì cho bạn? 😊"
        )
        db.add(default)
        db.commit()
        agents = [default]
    return [_serialize(a) for a in agents]


@router.post("")
async def create_agent(body: AgentConfigCreate, db: Session = Depends(get_db)):
    agent = AgentConfig(id=str(uuid.uuid4()), **body.dict())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return _serialize(agent)


@router.put("/{agent_id}")
async def update_agent(agent_id: str, body: AgentConfigUpdate, db: Session = Depends(get_db)):
    agent = db.query(AgentConfig).filter(AgentConfig.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    for field, val in body.dict(exclude_none=True).items():
        setattr(agent, field, val)
    db.commit()
    db.refresh(agent)
    return _serialize(agent)


def _serialize(a: AgentConfig) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "platform": a.platform,
        "system_prompt": a.system_prompt,
        "temperature": a.temperature,
        "auto_reply": a.auto_reply,
        "confidence_threshold": a.confidence_threshold,
        "greeting_message": a.greeting_message,
        "is_active": a.is_active,
        "created_at": a.created_at.isoformat() if a.created_at else None
    }
