"""Application configuration."""

import os
import json
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "LottoLab"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="production")
    
    # Database - Read from environment
    DATABASE_URL: str = Field(
        default=os.getenv("DATABASE_URL", "mysql+pymysql://user:password@localhost:3306/database")
    )
    DATABASE_POOL_SIZE: int = Field(default=10)
    DATABASE_MAX_OVERFLOW: int = Field(default=20)
    DATABASE_POOL_TIMEOUT: int = Field(default=30)
    
    # API
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:8044"]
    )
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = Field(default=os.getenv("SECRET_KEY", "change-me-in-production"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """Parse ALLOWED_ORIGINS from string or list."""
        if isinstance(v, str):
            # Try to parse as JSON array
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                # Fallback: split by comma
                return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
