"""Application configuration - Copy this to settings.py and fill in your values."""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "LottoLab"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="production")
    
    # Database - CHANGE THESE!
    DATABASE_URL: str = Field(
        default="mysql+pymysql://YOUR_USER:YOUR_PASSWORD@localhost:3306/YOUR_DATABASE"
    )
    DATABASE_POOL_SIZE: int = Field(default=10)
    DATABASE_MAX_OVERFLOW: int = Field(default=20)
    DATABASE_POOL_TIMEOUT: int = Field(default=30)
    
    # API - CHANGE THIS!
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:8044", "https://YOUR_DOMAIN.com"]
    )
    API_V1_PREFIX: str = "/api/v1"
    
    # Security - CHANGE THIS!
    SECRET_KEY: str = Field(default="CHANGE_THIS_TO_A_RANDOM_SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
