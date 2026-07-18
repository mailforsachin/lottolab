"""Strategy model - algorithm definitions."""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON

from backend.database.base import Base

class Strategy(Base):
    """Represents a ticket generation strategy/algorithm."""
    
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    algorithm_type = Column(String(50), nullable=False)
    parameters = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(String(20), default="1.0.0")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "algorithm_type": self.algorithm_type,
            "parameters": self.parameters,
            "is_active": self.is_active,
            "version": self.version,
        }
