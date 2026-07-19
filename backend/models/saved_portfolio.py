"""Saved portfolio persistence models - authenticated user portfolios."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, DECIMAL, JSON, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from backend.database.base import Base
from backend.models.user import User


class SavedPortfolio(Base):
    """Saved structural portfolio snapshot belonging to a user."""

    __tablename__ = "saved_portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Snapshot metadata
    game_type = Column(String(50), nullable=False)
    portfolio_size = Column(Integer, nullable=False)
    requested_candidate_count = Column(Integer, nullable=False)
    generated_candidate_count = Column(Integer, nullable=False)
    unique_structural_candidate_count = Column(Integer, nullable=False)
    master_seed = Column(Integer, nullable=False)

    # Strategy info (JSON arrays)
    strategy_ids = Column(JSON, nullable=False)
    strategy_names = Column(JSON, nullable=False)

    # Structural score
    structural_score = Column(DECIMAL(10, 4), nullable=True)
    structural_metrics = Column(JSON, nullable=True)

    # Generator version
    generator_version = Column(String(20), nullable=False, default="1.0.0")

    # Training metadata (Phase 5A: left as NULL)
    training_cutoff_date = Column(Date, nullable=True)
    training_draw_count = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="saved_portfolios")
    tickets = relationship(
        "SavedPortfolioTicket",
        cascade="all, delete-orphan",
        back_populates="portfolio",
        order_by="SavedPortfolioTicket.position"
    )
    allocations = relationship(
        "SavedPortfolioAllocation",
        cascade="all, delete-orphan",
        back_populates="portfolio"
    )

    __table_args__ = (
        Index("idx_saved_portfolios_user_id_created_at", "user_id", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "game": self.game_type,
            "portfolio_size": self.portfolio_size,
            "requested_candidate_count": self.requested_candidate_count,
            "generated_candidate_count": self.generated_candidate_count,
            "unique_structural_candidate_count": self.unique_structural_candidate_count,
            "master_seed": self.master_seed,
            "strategy_ids": self.strategy_ids,
            "strategy_names": self.strategy_names,
            "structural_optimizer_score": float(self.structural_score) if self.structural_score else None,
            "structural_optimizer_metrics": self.structural_metrics,
            "version": self.generator_version,
            "created_at": self.created_at.isoformat(),
            "training_cutoff_date": self.training_cutoff_date.isoformat() if self.training_cutoff_date else None,
            "training_draw_count": self.training_draw_count,
        }


class SavedPortfolioTicket(Base):
    """Individual ticket within a saved portfolio."""

    __tablename__ = "saved_portfolio_tickets"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("saved_portfolios.id"), nullable=False, index=True)
    position = Column(Integer, nullable=False)  # 0-based index

    numbers = Column(JSON, nullable=False)
    grand_number = Column(Integer, nullable=True)
    strategy_ids = Column(JSON, nullable=True)  # List[int]
    strategy_names = Column(JSON, nullable=True)  # List[str]

    portfolio = relationship("SavedPortfolio", back_populates="tickets")

    __table_args__ = (
        UniqueConstraint("portfolio_id", "position", name="uq_saved_portfolio_tickets_position"),
        Index("idx_saved_portfolio_tickets_portfolio_id_position", "portfolio_id", "position"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "numbers": self.numbers,
            "grand_number": self.grand_number,
            "strategy_ids": self.strategy_ids,
            "strategy_names": self.strategy_names,
        }


class SavedPortfolioAllocation(Base):
    """Per-strategy allocation within a saved portfolio."""

    __tablename__ = "saved_portfolio_allocations"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("saved_portfolios.id"), nullable=False, index=True)

    strategy_id = Column(Integer, nullable=False)
    strategy_name = Column(String(100), nullable=False)
    requested = Column(Integer, nullable=False)
    generated = Column(Integer, nullable=False)
    derived_seed = Column(Integer, nullable=False)

    portfolio = relationship("SavedPortfolio", back_populates="allocations")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "requested": self.requested,
            "generated": self.generated,
            "derived_seed": self.derived_seed,
        }
