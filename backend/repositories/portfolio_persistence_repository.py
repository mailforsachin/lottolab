"""Repository for saved portfolio persistence operations."""

from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models.saved_portfolio import SavedPortfolio, SavedPortfolioTicket, SavedPortfolioAllocation


class PortfolioPersistenceRepository:
    """Data access for saved portfolios with user scoping."""

    def save(
        self,
        session: Session,
        user_id: int,
        portfolio_data: dict
    ) -> SavedPortfolio:
        """
        Save a portfolio with tickets and allocations.

        Args:
            session: SQLAlchemy session
            user_id: ID of the user owning the portfolio
            portfolio_data: Dictionary with portfolio snapshot

        Returns:
            Created SavedPortfolio instance

        Raises:
            ValueError: On validation failure
        """
        # Extract training metadata
        training_cutoff_date = portfolio_data.get("training_cutoff_date")
        if training_cutoff_date and isinstance(training_cutoff_date, str):
            from datetime import date
            training_cutoff_date = date.fromisoformat(training_cutoff_date)

        # Create portfolio record
        portfolio = SavedPortfolio(
            user_id=user_id,
            game_type=portfolio_data["game"],
            portfolio_size=portfolio_data["portfolio_size"],
            requested_candidate_count=portfolio_data["requested_candidate_count"],
            generated_candidate_count=portfolio_data["generated_candidate_count"],
            unique_structural_candidate_count=portfolio_data["unique_structural_candidate_count"],
            master_seed=portfolio_data["master_seed"],
            strategy_ids=portfolio_data["strategy_ids"],
            strategy_names=portfolio_data["strategy_names"],
            structural_score=portfolio_data.get("structural_optimizer_score"),
            structural_metrics=portfolio_data.get("structural_optimizer_metrics"),
            generator_version=portfolio_data.get("version", "1.0.0"),
            training_cutoff_date=training_cutoff_date,
            training_draw_count=portfolio_data.get("training_draw_count", 0),
        )

        session.add(portfolio)
        session.flush()  # Get portfolio.id

        # Create tickets
        for idx, ticket_data in enumerate(portfolio_data["selected_tickets"]):
            ticket = SavedPortfolioTicket(
                portfolio_id=portfolio.id,
                position=idx,
                numbers=ticket_data["numbers"],
                grand_number=ticket_data.get("grand_number"),
                strategy_ids=ticket_data.get("strategy_ids"),
                strategy_names=ticket_data.get("strategy_names"),
            )
            session.add(ticket)

        # Create allocations
        for alloc_data in portfolio_data["per_strategy_allocations"]:
            allocation = SavedPortfolioAllocation(
                portfolio_id=portfolio.id,
                strategy_id=alloc_data["strategy_id"],
                strategy_name=alloc_data["strategy_name"],
                requested=alloc_data["requested"],
                generated=alloc_data["generated"],
                derived_seed=alloc_data["derived_seed"],
            )
            session.add(allocation)

        return portfolio

    def list_by_user(
        self,
        session: Session,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[SavedPortfolio], int]:
        """
        List portfolios for a user with pagination.

        Returns:
            Tuple of (portfolios list, total count)
        """
        query = session.query(SavedPortfolio).filter(
            SavedPortfolio.user_id == user_id
        ).order_by(
            SavedPortfolio.created_at.desc()
        )

        total = query.count()
        portfolios = query.offset(offset).limit(limit).all()

        return portfolios, total

    def count_by_user(
        self,
        session: Session,
        user_id: int
    ) -> int:
        """
        Count portfolios for a user.

        Returns:
            Total count of portfolios owned by the user
        """
        return session.query(SavedPortfolio).filter(
            SavedPortfolio.user_id == user_id
        ).count()

    def get_by_id(
        self,
        session: Session,
        portfolio_id: int,
        user_id: int
    ) -> Optional[SavedPortfolio]:
        """
        Get a portfolio by ID, scoped to user.

        Returns None if not found or not owned by user.
        """
        return session.query(SavedPortfolio).filter(
            SavedPortfolio.id == portfolio_id,
            SavedPortfolio.user_id == user_id
        ).first()

    def delete(
        self,
        session: Session,
        portfolio_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a portfolio by ID, scoped to user.

        Returns True if deleted, False if not found or not owned.
        """
        portfolio = self.get_by_id(session, portfolio_id, user_id)
        if not portfolio:
            return False

        session.delete(portfolio)
        return True
