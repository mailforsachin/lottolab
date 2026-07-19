"""Service for portfolio persistence business logic."""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from backend.models.saved_portfolio import SavedPortfolio
from backend.repositories.portfolio_persistence_repository import PortfolioPersistenceRepository


class PortfolioPersistenceService:
    """Business logic for saving and retrieving portfolios."""

    def __init__(self):
        self.repository = PortfolioPersistenceRepository()

    def save_portfolio(
        self,
        session: Session,
        user_id: int,
        snapshot: Dict[str, Any]
    ) -> SavedPortfolio:
        """
        Save a portfolio snapshot atomically.

        Args:
            session: SQLAlchemy session (transaction owner)
            user_id: ID of the user owning the portfolio
            snapshot: Complete portfolio snapshot

        Returns:
            Created SavedPortfolio instance

        Raises:
            ValueError: On validation failure
        """
        try:
            portfolio = self.repository.save(session, user_id, snapshot)
            session.commit()
            session.refresh(portfolio)
            return portfolio
        except Exception as e:
            session.rollback()
            raise

    def list_portfolios(
        self,
        session: Session,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List portfolios for a user.

        Returns:
            Dictionary with portfolios and pagination metadata
        """
        portfolios, total = self.repository.list_by_user(session, user_id, limit, offset)

        return {
            "portfolios": [self._format_list_item(p) for p in portfolios],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_portfolio(
        self,
        session: Session,
        portfolio_id: int,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a portfolio by ID, scoped to user.

        Returns None if not found or not owned by user.
        """
        portfolio = self.repository.get_by_id(session, portfolio_id, user_id)
        if not portfolio:
            return None

        return self._format_detail(portfolio)

    def delete_portfolio(
        self,
        session: Session,
        portfolio_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a portfolio by ID, scoped to user.

        Returns True if deleted, False if not found or not owned.
        """
        try:
            deleted = self.repository.delete(session, portfolio_id, user_id)
            if deleted:
                session.commit()
            return deleted
        except Exception:
            session.rollback()
            raise

    def _format_list_item(self, portfolio: SavedPortfolio) -> Dict[str, Any]:
        """Format portfolio for listing response."""
        return {
            "id": portfolio.id,
            "game_type": portfolio.game_type,
            "portfolio_size": portfolio.portfolio_size,
            "created_at": portfolio.created_at.isoformat(),
            "structural_score": float(portfolio.structural_score) if portfolio.structural_score else None,
        }

    def _format_detail(self, portfolio: SavedPortfolio) -> Dict[str, Any]:
        """Format portfolio for detail response."""
        tickets = portfolio.tickets
        allocations = portfolio.allocations

        return {
            "id": portfolio.id,
            "game": portfolio.game_type,
            "portfolio_size": portfolio.portfolio_size,
            "selected_tickets": [t.to_dict() for t in tickets],
            "strategy_ids": portfolio.strategy_ids,
            "strategy_names": portfolio.strategy_names,
            "requested_candidate_count": portfolio.requested_candidate_count,
            "generated_candidate_count": portfolio.generated_candidate_count,
            "unique_structural_candidate_count": portfolio.unique_structural_candidate_count,
            "master_seed": portfolio.master_seed,
            "per_strategy_allocations": [a.to_dict() for a in allocations],
            "structural_optimizer_score": float(portfolio.structural_score) if portfolio.structural_score else None,
            "structural_optimizer_metrics": portfolio.structural_metrics,
            "version": portfolio.generator_version,
            "created_at": portfolio.created_at.isoformat(),
            "training_cutoff_date": portfolio.training_cutoff_date.isoformat() if portfolio.training_cutoff_date else None,
            "training_draw_count": portfolio.training_draw_count,
        }
