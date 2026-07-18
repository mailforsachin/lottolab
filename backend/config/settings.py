"""Application configuration using Pydantic Settings."""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "LottoLab"
    DEBUG: bool = Field(default=True)
    ENVIRONMENT: str = Field(default="development")
    
    # Database - Updated with correct password
    DATABASE_URL: str = Field(
        default="mysql+pymysql://lottolab:LottoLab2024!@localhost:3306/lottolab"
    )
    DATABASE_POOL_SIZE: int = Field(default=10)
    DATABASE_MAX_OVERFLOW: int = Field(default=20)
    DATABASE_POOL_TIMEOUT: int = Field(default=30)
    
    # API - Updated to include port 8044
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:8044", "http://localhost:3000", "http://localhost:8000"]
    )
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """Parse comma-separated origins or return as list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

# Create global settings instance
settings = Settings()
