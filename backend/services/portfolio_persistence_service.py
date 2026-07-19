"""
Portfolio persistence service for LottoLab.

Handles saving, retrieving, listing, and deleting saved portfolios.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.models.saved_portfolio import SavedPortfolio, SavedPortfolioTicket, SavedPortfolioAllocation
from backend.repositories.portfolio_persistence_repository import PortfolioPersistenceRepository


class PortfolioPersistenceService:
    """Service for portfolio persistence operations."""

    def __init__(self):
        self.repository = PortfolioPersistenceRepository()

    def save_portfolio(
        self,
        session: Session,
        user_id: int,
        snapshot: Dict[str, Any]
    ) -> SavedPortfolio:
        """
        Save a portfolio snapshot for a user.

        Args:
            session: Database session
            user_id: User ID
            snapshot: Portfolio snapshot from generation endpoint

        Returns:
            SavedPortfolio object

        Raises:
            ValueError: For validation errors
            SQLAlchemyError: For database errors
        """
        try:
            portfolio = self.repository.save(session, user_id, snapshot)
            session.commit()
            session.refresh(portfolio)
            return portfolio

        except (ValueError, TypeError) as e:
            session.rollback()
            raise ValueError(f"Invalid portfolio snapshot: {str(e)}") from e
        except SQLAlchemyError as e:
            session.rollback()
            raise SQLAlchemyError(f"Database error saving portfolio: {str(e)}") from e

    def get_portfolio(
        self,
        session: Session,
        portfolio_id: int,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a saved portfolio with ownership verification.

        Args:
            session: Database session
            portfolio_id: Portfolio ID
            user_id: User ID for ownership check

        Returns:
            Portfolio dict or None if not found or not owned
        """
        portfolio = self.repository.get_by_id(session, portfolio_id, user_id)

        if not portfolio:
            return None

        return self._portfolio_to_dict(portfolio)

    def list_portfolios(
        self,
        session: Session,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List saved portfolios for a user.

        Args:
            session: Database session
            user_id: User ID
            limit: Max number of portfolios
            offset: Pagination offset

        Returns:
            Dict with 'portfolios' list and 'total' count
        """
        portfolios, total = self.repository.list_by_user(
            session,
            user_id,
            limit=limit,
            offset=offset
        )

        return {
            'portfolios': [self._portfolio_to_dict(p) for p in portfolios],
            'total': total,
            'limit': limit,
            'offset': offset
        }

    def delete_portfolio(
        self,
        session: Session,
        portfolio_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a saved portfolio with ownership verification.

        Args:
            session: Database session
            portfolio_id: Portfolio ID
            user_id: User ID for ownership check

        Returns:
            True if deleted, False if not found or not owned
        """
        try:
            return self.repository.delete(session, portfolio_id, user_id)
        except SQLAlchemyError:
            return False

    def _portfolio_to_dict(self, portfolio: SavedPortfolio) -> Dict[str, Any]:
        """Convert SavedPortfolio to dict for API response."""
        tickets = []
        for ticket in portfolio.tickets:
            tickets.append({
                'numbers': ticket.numbers,
                'grand_number': ticket.grand_number,
                'strategy_ids': ticket.strategy_ids,
                'strategy_names': ticket.strategy_names
            })

        allocations = []
        for alloc in portfolio.allocations:
            allocations.append({
                'strategy_id': alloc.strategy_id,
                'strategy_name': alloc.strategy_name,
                'requested': alloc.requested,
                'generated': alloc.generated,
                'derived_seed': alloc.derived_seed
            })

        return {
            'id': portfolio.id,
            'game': portfolio.game_type,
            'portfolio_size': portfolio.portfolio_size,
            'selected_tickets': tickets,
            'strategy_ids': portfolio.strategy_ids,
            'strategy_names': portfolio.strategy_names,
            'requested_candidate_count': portfolio.requested_candidate_count,
            'generated_candidate_count': portfolio.generated_candidate_count,
            'unique_structural_candidate_count': portfolio.unique_structural_candidate_count,
            'master_seed': portfolio.master_seed,
            'per_strategy_allocations': allocations,
            'structural_optimizer_score': float(portfolio.structural_score) if portfolio.structural_score else None,
            'structural_optimizer_metrics': portfolio.structural_metrics,
            'version': portfolio.generator_version,
            'created_at': portfolio.created_at.isoformat() if portfolio.created_at else None,
            'training_cutoff_date': portfolio.training_cutoff_date.isoformat()
                if portfolio.training_cutoff_date else None,
            'training_draw_count': portfolio.training_draw_count
        }
