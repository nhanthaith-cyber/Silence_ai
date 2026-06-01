from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, Enum, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
import uuid


def gen_uuid():
    return str(uuid.uuid4())


class PlatformEnum(str, enum.Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    SHOPEE = "shopee"
    TIKTOK = "tiktok"
    NHANH_VN = "nhanh_vn"


class ConversationStatus(str, enum.Enum):
    OPEN = "open"
    AI_HANDLING = "ai_handling"
    WAITING_HUMAN = "waiting_human"
    HUMAN_HANDLING = "human_handling"
    RESOLVED = "resolved"
    CLOSED = "closed"


class MessageDirection(str, enum.Enum):
    INBOUND = "inbound"   # Khách gửi
    OUTBOUND = "outbound"  # Agent/AI gửi


class TicketCategory(str, enum.Enum):
    ORDER = "order"
    RETURN = "return"
    COMPLAINT = "complaint"
    SHIPPING = "shipping"
    PRODUCT = "product"
    PAYMENT = "payment"
    GENERAL = "general"


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=gen_uuid)
    platform = Column(Enum(PlatformEnum), nullable=False)
    platform_conversation_id = Column(String, nullable=False, index=True)
    customer_id = Column(String, nullable=False)
    customer_name = Column(String, default="Khách hàng")
    customer_avatar = Column(String, nullable=True)
    status = Column(Enum(ConversationStatus), default=ConversationStatus.OPEN)
    assigned_agent = Column(String, nullable=True)
    last_message = Column(Text, nullable=True)
    last_message_at = Column(DateTime(timezone=True), server_default=func.now())
    unread_count = Column(Integer, default=0)
    ai_confidence = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    ticket = relationship("Ticket", back_populates="conversation", uselist=False)


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    direction = Column(Enum(MessageDirection), nullable=False)
    sender_name = Column(String, default="")
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    is_ai_generated = Column(Boolean, default=False)
    ai_confidence = Column(Float, nullable=True)
    platform_message_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, default=gen_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    category = Column(Enum(TicketCategory), default=TicketCategory.GENERAL)
    priority = Column(String, default="normal")  # low, normal, high, urgent
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="open")  # open, in_progress, resolved, closed
    assigned_agent = Column(String, nullable=True)
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    conversation = relationship("Conversation", back_populates="ticket")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id = Column(String, primary_key=True, default=gen_uuid)
    category = Column(String, default="general")
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    tags = Column(Text, default="")  # comma-separated tags
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False, default="AI Assistant")
    platform = Column(String, default="all")  # all, facebook, instagram, shopee, tiktok
    system_prompt = Column(Text, nullable=False)
    temperature = Column(Float, default=0.7)
    auto_reply = Column(Boolean, default=True)
    confidence_threshold = Column(Float, default=0.7)  # dưới mức này → handoff
    greeting_message = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=gen_uuid)
    filename = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True, default=gen_uuid)
    document_id = Column(String, ForeignKey("documents.id"))
    chunk_text = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=False)  # Luu vector duoi dang JSON chuoi [0.1, 0.2, ...]
    
    document = relationship("Document", back_populates="chunks")


class CustomerMemory(Base):
    """Bộ nhớ khách hàng — lưu sở thích, lịch sử và thông tin cá nhân hoá."""
    __tablename__ = "customer_memories"

    id = Column(String, primary_key=True, default=gen_uuid)
    customer_id = Column(String, nullable=False, index=True)
    platform = Column(String, default="all")
    preferred_sizes = Column(Text, default="{}")  # JSON: {"top": "M", "bottom": "L"}
    preferred_fit = Column(String, nullable=True)  # relaxed, regular, slim, oversized
    style_preferences = Column(String, nullable=True)  # minimalist, streetwear, classic
    purchase_history_summary = Column(Text, nullable=True)  # Tóm tắt lịch sử mua
    last_purchase_date = Column(DateTime, nullable=True)
    complaint_history = Column(Text, nullable=True)
    price_sensitivity = Column(String, default="medium")  # low, medium, high
    satisfaction_score = Column(Float, default=0.5)  # 0.0 - 1.0
    communication_style = Column(String, default="casual")  # formal, casual, brief
    body_measurements = Column(Text, default="{}")  # JSON: {"height": 172, "weight": 68}
    notes = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # TTL
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Product(Base):
    """Sản phẩm thời trang — quần áo, phụ kiện với thông tin size, chất liệu, giá."""
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=False)  # ao, quan, jacket, phu_kien
    subcategory = Column(String, nullable=True)  # polo, tshirt, hoodie, jean, chino...
    description = Column(Text, nullable=True)
    price = Column(Integer, nullable=False)  # VND
    sale_price = Column(Integer, nullable=True)  # Giá sale
    sizes_available = Column(Text, default="{}")  # JSON: {"S": 5, "M": 12, "L": 8}
    size_chart = Column(Text, default="{}")  # JSON bảng đo size
    fabric = Column(String, nullable=True)  # cotton 100%, denim, linen...
    fabric_properties = Column(Text, default="{}")  # JSON: {"stretch": true, "shrinkage": "2-3%"}
    fit_type = Column(String, default="regular")  # relaxed, regular, slim, oversized
    color = Column(String, nullable=True)
    images = Column(Text, default="[]")  # JSON array URLs hình ảnh
    care_instructions = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ShopIntegration(Base):
    __tablename__ = "shop_integrations"

    id = Column(String, primary_key=True, default=gen_uuid)
    shop_id = Column(String, nullable=False, index=True)
    platform = Column(Enum(PlatformEnum), nullable=False)
    shop_name = Column(String, nullable=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(Integer, nullable=True)
    refresh_expires_at = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
