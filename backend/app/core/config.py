from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./cs_agent.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    MULTI_AGENT_ENABLED: bool = True

    # Facebook / Instagram
    FACEBOOK_PAGE_TOKEN: str = ""
    FACEBOOK_APP_SECRET: str = ""
    FACEBOOK_VERIFY_TOKEN: str = "silence_verify_2024"
    INSTAGRAM_ACCESS_TOKEN: str = ""
    
    # Shopee
    SHOPEE_PARTNER_ID: str = ""
    SHOPEE_PARTNER_KEY: str = ""
    SHOPEE_API_BASE_URL: str = "https://partner.shopeemobile.com"  # Production
    
    # TikTok (mock trong MVP)
    TIKTOK_APP_KEY: str = ""
    TIKTOK_APP_SECRET: str = ""
    
    # Nhanh.vn
    NHANH_APP_ID: str = ""
    NHANH_SECRET_KEY: str = ""
    
    # App
    SECRET_KEY: str = "your-secret-key-change-in-production"
    DEBUG: bool = False
    FRONTEND_URL: str = ""
    PORT: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()
