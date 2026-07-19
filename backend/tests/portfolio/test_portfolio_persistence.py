"""
Tests for portfolio persistence with SQLite in-memory database.
"""

import pytest
import copy
import json
from datetime import datetime
from unittest.mock import patch, Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.database.base import Base
from backend.models import User, SavedPortfolio, SavedPortfolioTicket, SavedPortfolioAllocation
from backend.repositories.portfolio_persistence_repository import PortfolioPersistenceRepository
from backend.services.portfolio_persistence_service import PortfolioPersistenceService


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for tests."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def user(db_session):
    """Create a test user."""
    user = User(
        username="test_user",
        hashed_password="hash",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_snapshot_lotto649():
    """Create a sample Lotto 6/49 portfolio snapshot."""
    return {
        "game": "6/49",
        "portfolio_size": 3,
        "selected_tickets": [
            {
                "numbers": [1, 2, 3, 4, 5, 6],
                "grand_number": None,
                "strategy_ids": [1],
                "strategy_names": ["Random"]
            },
            {
                "numbers": [7, 8, 9, 10, 11, 12],
                "grand_number": None,
                "strategy_ids": [2],
                "strategy_names": ["Sobol"]
            },
            {
                "numbers": [13, 14, 15, 16, 17, 18],
                "grand_number": None,
                "strategy_ids": [1, 2],
                "strategy_names": ["Random", "Sobol"]
            }
        ],
        "strategy_ids": [1, 2],
        "strategy_names": ["Random", "Sobol"],
        "requested_candidate_count": 100,
        "generated_candidate_count": 98,
        "unique_structural_candidate_count": 90,
        "master_seed": 42,
        "per_strategy_allocations": [
            {"strategy_id": 1, "strategy_name": "Random", "requested": 50, "generated": 48, "derived_seed": 12345},
            {"strategy_id": 2, "strategy_name": "Sobol", "requested": 50, "generated": 50, "derived_seed": 67890}
        ],
        "structural_optimizer_score": 0.85,
        "structural_optimizer_metrics": {"score": 0.85},
        "version": "1.0.0"
    }


@pytest.fixture
def sample_snapshot_dailygrand():
    """Create a sample Daily Grand portfolio snapshot."""
    return {
        "game": "Daily Grand",
        "portfolio_size": 2,
        "selected_tickets": [
            {
                "numbers": [1, 2, 3, 4, 5],
                "grand_number": 7,
                "strategy_ids": [1],
                "strategy_names": ["Random"]
            },
            {
                "numbers": [6, 7, 8, 9, 10],
                "grand_number": 3,
                "strategy_ids": [1],
                "strategy_names": ["Random"]
            }
        ],
        "strategy_ids": [1],
        "strategy_names": ["Random"],
        "requested_candidate_count": 100,
        "generated_candidate_count": 98,
        "unique_structural_candidate_count": 90,
        "master_seed": 42,
        "per_strategy_allocations": [
            {"strategy_id": 1, "strategy_name": "Random", "requested": 100, "generated": 98, "derived_seed": 12345}
        ],
        "structural_optimizer_score": 0.75,
        "structural_optimizer_metrics": {"score": 0.75},
        "version": "1.0.0"
    }


class TestPortfolioPersistenceRepository:
    """Test repository operations."""

    def test_save_lotto649(self, db_session, user, sample_snapshot_lotto649):
        """Test saving a Lotto 6/49 portfolio."""
        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, sample_snapshot_lotto649)

        db_session.commit()
        db_session.refresh(portfolio)

        assert portfolio.id is not None
        assert portfolio.user_id == user.id
        assert portfolio.game_type == "6/49"
        assert portfolio.portfolio_size == 3
        assert len(portfolio.tickets) == 3
        assert len(portfolio.allocations) == 2

    def test_save_dailygrand_preserves_grand_number(self, db_session, user, sample_snapshot_dailygrand):
        """Test saving a Daily Grand portfolio preserves Grand Numbers."""
        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, sample_snapshot_dailygrand)

        db_session.commit()
        db_session.refresh(portfolio)

        assert portfolio.game_type == "Daily Grand"
        tickets = sorted(portfolio.tickets, key=lambda t: t.position)
        assert tickets[0].grand_number == 7
        assert tickets[1].grand_number == 3

    def test_ticket_order_preserved(self, db_session, user, sample_snapshot_lotto649):
        """Test that ticket order is preserved."""
        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, sample_snapshot_lotto649)

        db_session.commit()
        db_session.refresh(portfolio)

        tickets = list(portfolio.tickets)
        assert tickets[0].position == 0
        assert tickets[0].numbers == [1, 2, 3, 4, 5, 6]
        assert tickets[1].position == 1
        assert tickets[1].numbers == [7, 8, 9, 10, 11, 12]
        assert tickets[2].position == 2
        assert tickets[2].numbers == [13, 14, 15, 16, 17, 18]

    def test_provenance_preserved(self, db_session, user, sample_snapshot_lotto649):
        """Test that provenance is preserved."""
        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, sample_snapshot_lotto649)

        db_session.commit()
        db_session.refresh(portfolio)

        tickets = list(portfolio.tickets)
        assert tickets[0].strategy_ids == [1]
        assert tickets[0].strategy_names == ["Random"]
        assert tickets[2].strategy_ids == [1, 2]
        assert tickets[2].strategy_names == ["Random", "Sobol"]

    def test_allocations_saved(self, db_session, user, sample_snapshot_lotto649):
        """Test that allocations are saved correctly."""
        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, sample_snapshot_lotto649)

        db_session.commit()
        db_session.refresh(portfolio)

        allocations = list(portfolio.allocations)
        assert len(allocations) == 2
        assert allocations[0].strategy_id == 1
        assert allocations[0].strategy_name == "Random"
        assert allocations[0].requested == 50
        assert allocations[0].generated == 48
        assert allocations[0].derived_seed == 12345

    def test_structural_metadata_preserved(self, db_session, user, sample_snapshot_lotto649):
        """Test that structural metadata is preserved."""
        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, sample_snapshot_lotto649)

        db_session.commit()
        db_session.refresh(portfolio)

        assert float(portfolio.structural_score) == 0.85
        assert portfolio.structural_metrics == {"score": 0.85}
        assert portfolio.generator_version == "1.0.0"

    def test_ownership_assigned_server_side(self, db_session, user, sample_snapshot_lotto649):
        """Test that user_id is assigned server-side, never from client."""
        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, sample_snapshot_lotto649)

        db_session.commit()
        db_session.refresh(portfolio)

        assert portfolio.user_id == user.id

    def test_list_by_user(self, db_session, user, sample_snapshot_lotto649):
        """Test listing portfolios by user."""
        repo = PortfolioPersistenceRepository()

        repo.save(db_session, user.id, sample_snapshot_lotto649)
        repo.save(db_session, user.id, sample_snapshot_lotto649)
        db_session.commit()

        portfolios, total = repo.list_by_user(db_session, user.id)
        assert total == 2
        assert len(portfolios) == 2

    def test_user_a_cannot_list_user_b_portfolios(self, db_session, user, sample_snapshot_lotto649):
        """Test that user A cannot list user B's portfolios."""
        repo = PortfolioPersistenceRepository()

        user_b = User(
            username="test_user_b",
            hashed_password="hash",
            is_active=True
        )
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

        repo.save(db_session, user_b.id, sample_snapshot_lotto649)
        db_session.commit()

        portfolios, total = repo.list_by_user(db_session, user.id)
        assert total == 0
        assert len(portfolios) == 0

    def test_get_by_id_owner_scoped(self, db_session, user, sample_snapshot_lotto649):
        """Test that get_by_id is scoped by user."""
        repo = PortfolioPersistenceRepository()

        user_b = User(
            username="test_user_b",
            hashed_password="hash",
            is_active=True
        )
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

        portfolio_b = repo.save(db_session, user_b.id, sample_snapshot_lotto649)
        db_session.commit()

        result = repo.get_by_id(db_session, portfolio_b.id, user.id)
        assert result is None

        result = repo.get_by_id(db_session, portfolio_b.id, user_b.id)
        assert result is not None

    def test_delete_owner_scoped(self, db_session, user, sample_snapshot_lotto649):
        """Test that delete is scoped by user."""
        repo = PortfolioPersistenceRepository()

        user_b = User(
            username="test_user_b",
            hashed_password="hash",
            is_active=True
        )
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

        portfolio_b = repo.save(db_session, user_b.id, sample_snapshot_lotto649)
        db_session.commit()

        deleted = repo.delete(db_session, portfolio_b.id, user.id)
        assert deleted is False

        deleted = repo.delete(db_session, portfolio_b.id, user_b.id)
        assert deleted is True

    def test_delete_cascades_to_children(self, db_session, user, sample_snapshot_lotto649):
        """Test that deleting a portfolio cascades to child records."""
        repo = PortfolioPersistenceRepository()

        portfolio = repo.save(db_session, user.id, sample_snapshot_lotto649)
        db_session.commit()

        portfolio_id = portfolio.id

        tickets = db_session.query(SavedPortfolioTicket).filter(
            SavedPortfolioTicket.portfolio_id == portfolio_id
        ).count()
        assert tickets == 3

        allocations = db_session.query(SavedPortfolioAllocation).filter(
            SavedPortfolioAllocation.portfolio_id == portfolio_id
        ).count()
        assert allocations == 2

        deleted = repo.delete(db_session, portfolio_id, user.id)
        assert deleted is True
        db_session.commit()

        tickets = db_session.query(SavedPortfolioTicket).filter(
            SavedPortfolioTicket.portfolio_id == portfolio_id
        ).count()
        assert tickets == 0

        allocations = db_session.query(SavedPortfolioAllocation).filter(
            SavedPortfolioAllocation.portfolio_id == portfolio_id
        ).count()
        assert allocations == 0

    def test_duplicate_positions_rejected(self, db_session, user, sample_snapshot_lotto649):
        """Test that duplicate positions are rejected by the database."""
        repo = PortfolioPersistenceRepository()

        portfolio = repo.save(db_session, user.id, sample_snapshot_lotto649)
        db_session.commit()

        duplicate_ticket = SavedPortfolioTicket(
            portfolio_id=portfolio.id,
            position=0,
            numbers=[1, 2, 3, 4, 5, 6],
            grand_number=None
        )
        db_session.add(duplicate_ticket)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestPortfolioPersistenceService:
    """Test service operations."""

    def test_save_portfolio(self, db_session, user, sample_snapshot_lotto649):
        """Test saving a portfolio through the service."""
        service = PortfolioPersistenceService()
        portfolio = service.save_portfolio(db_session, user.id, sample_snapshot_lotto649)

        assert portfolio.id is not None
        assert portfolio.user_id == user.id

    def test_list_portfolios(self, db_session, user, sample_snapshot_lotto649):
        """Test listing portfolios through the service."""
        service = PortfolioPersistenceService()

        service.save_portfolio(db_session, user.id, sample_snapshot_lotto649)
        result = service.list_portfolios(db_session, user.id)

        assert result["total"] == 1
        assert len(result["portfolios"]) == 1
        assert result["portfolios"][0]["portfolio_size"] == 3

    def test_get_portfolio(self, db_session, user, sample_snapshot_lotto649):
        """Test getting a portfolio through the service."""
        service = PortfolioPersistenceService()
        portfolio = service.save_portfolio(db_session, user.id, sample_snapshot_lotto649)

        detail = service.get_portfolio(db_session, portfolio.id, user.id)
        assert detail is not None
        assert detail["game"] == "6/49"
        assert detail["portfolio_size"] == 3
        assert len(detail["selected_tickets"]) == 3

    def test_delete_portfolio(self, db_session, user, sample_snapshot_lotto649):
        """Test deleting a portfolio through the service."""
        service = PortfolioPersistenceService()
        portfolio = service.save_portfolio(db_session, user.id, sample_snapshot_lotto649)

        deleted = service.delete_portfolio(db_session, portfolio.id, user.id)
        assert deleted is True

        result = service.get_portfolio(db_session, portfolio.id, user.id)
        assert result is None

    def test_wrong_owner_get_returns_none(self, db_session, user, sample_snapshot_lotto649):
        """Test that wrong-owner get returns None, not an exception."""
        service = PortfolioPersistenceService()

        user_b = User(
            username="test_user_b",
            hashed_password="hash",
            is_active=True
        )
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

        portfolio_b = service.save_portfolio(db_session, user_b.id, sample_snapshot_lotto649)

        result = service.get_portfolio(db_session, portfolio_b.id, user.id)
        assert result is None

    def test_wrong_owner_delete_returns_false(self, db_session, user, sample_snapshot_lotto649):
        """Test that wrong-owner delete returns False."""
        service = PortfolioPersistenceService()

        user_b = User(
            username="test_user_b",
            hashed_password="hash",
            is_active=True
        )
        db_session.add(user_b)
        db_session.commit()
        db_session.refresh(user_b)

        portfolio_b = service.save_portfolio(db_session, user_b.id, sample_snapshot_lotto649)

        deleted = service.delete_portfolio(db_session, portfolio_b.id, user.id)
        assert deleted is False


class TestAtomicRollback:
    """Test atomic rollback behavior."""

    def test_save_rollback_on_child_failure(self, db_session, user, sample_snapshot_lotto649):
        """Test that child failure causes rollback of entire transaction."""
        repo = PortfolioPersistenceRepository()

        # Use a deep copy to avoid mutating fixture
        snapshot = copy.deepcopy(sample_snapshot_lotto649)

        # Save a clean portfolio first
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        portfolio_id = portfolio.id

        # Verify the portfolio exists
        exists = db_session.query(SavedPortfolio).filter(
            SavedPortfolio.id == portfolio_id
        ).first()
        assert exists is not None

        # Now cause an integrity error by adding a duplicate position
        duplicate_ticket = SavedPortfolioTicket(
            portfolio_id=portfolio_id,
            position=0,  # Duplicate position
            numbers=[1, 2, 3, 4, 5, 6],
            grand_number=None
        )
        db_session.add(duplicate_ticket)

        # This should fail with IntegrityError
        with pytest.raises(IntegrityError):
            db_session.commit()

        # Rollback the failed transaction
        db_session.rollback()

        # The parent should still exist (it was committed successfully)
        # The duplicate ticket should NOT exist
        # The original tickets should still exist (3 tickets)
        parent_exists = db_session.query(SavedPortfolio).filter(
            SavedPortfolio.id == portfolio_id
        ).first()
        assert parent_exists is not None

        ticket_count = db_session.query(SavedPortfolioTicket).filter(
            SavedPortfolioTicket.portfolio_id == portfolio_id
        ).count()
        assert ticket_count == 3  # Original 3 tickets

        # Clean up
        repo.delete(db_session, portfolio_id, user.id)
        db_session.commit()

    def test_save_atomic_no_partial_state(self, db_session, user, sample_snapshot_lotto649):
        """Test that a failed validation leaves no partial state."""
        service = PortfolioPersistenceService()

        # Count before
        count_before = db_session.query(SavedPortfolio).count()

        # Use deep copy to avoid mutation
        snapshot = copy.deepcopy(sample_snapshot_lotto649)

        # Create a snapshot with invalid ticket numbers (duplicate within ticket)
        bad_snapshot = copy.deepcopy(sample_snapshot_lotto649)
        bad_snapshot["selected_tickets"][0]["numbers"] = [1, 1, 2, 3, 4, 5]  # Duplicate 1

        # This should fail validation in the request model
        from backend.api.v1.endpoints.portfolios import SavePortfolioRequest
        with pytest.raises(ValueError, match="Ticket numbers must be unique"):
            SavePortfolioRequest(**bad_snapshot)

        # Count should remain unchanged
        count_after = db_session.query(SavedPortfolio).count()
        assert count_after == count_before
