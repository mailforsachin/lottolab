"""
Phase 6 portfolio evaluation tests.
"""

import pytest
import copy
import json
from datetime import date, timedelta
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.models import User, SavedPortfolio, SavedPortfolioTicket, SavedPortfolioAllocation
from backend.models.draw import Draw
from backend.repositories.portfolio_persistence_repository import PortfolioPersistenceRepository
from backend.services.portfolio_evaluation_service import PortfolioEvaluationService
from backend.services.portfolio_persistence_service import PortfolioPersistenceService
from backend.core.algorithms.base import LOTTO_649, DAILY_GRAND


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
def sample_snapshot_with_cutoff():
    """Create a sample snapshot with training cutoff metadata."""
    return {
        "game": "6/49",
        "portfolio_size": 3,
        "selected_tickets": [
            {"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]},
            {"numbers": [7, 8, 9, 10, 11, 12], "grand_number": None, "strategy_ids": [2], "strategy_names": ["Sobol"]},
            {"numbers": [13, 14, 15, 16, 17, 18], "grand_number": None, "strategy_ids": [1, 2], "strategy_names": ["Random", "Sobol"]}
        ],
        "strategy_ids": [1, 2],
        "strategy_names": ["Random", "Sobol"],
        "requested_candidate_count": 30,
        "generated_candidate_count": 30,
        "unique_structural_candidate_count": 30,
        "master_seed": 42,
        "per_strategy_allocations": [
            {"strategy_id": 1, "strategy_name": "Random", "requested": 15, "generated": 15, "derived_seed": 12345},
            {"strategy_id": 2, "strategy_name": "Sobol", "requested": 15, "generated": 15, "derived_seed": 67890}
        ],
        "structural_optimizer_score": 0.85,
        "structural_optimizer_metrics": {"score": 0.85},
        "version": "1.0.0",
        "training_cutoff_date": "2026-07-15",
        "training_draw_count": 100
    }


class TestTrainingMetadataPropagation:
    """Tests for training metadata propagation through the pipeline."""

    def test_training_cutoff_captured_from_snapshot(self, db_session, user):
        """Test that training_cutoff_date comes from the training snapshot."""
        snapshot = {
            "game": "6/49",
            "portfolio_size": 1,
            "selected_tickets": [{"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]}],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [{"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}],
            "structural_optimizer_score": 0.85,
            "structural_optimizer_metrics": {"score": 0.85},
            "version": "1.0.0",
            "training_cutoff_date": "2026-07-15",
            "training_draw_count": 100
        }

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        assert portfolio.training_cutoff_date.isoformat() == "2026-07-15"
        assert portfolio.training_draw_count == 100

    def test_training_metadata_survives_save_retrieve(self, db_session, user, sample_snapshot_with_cutoff):
        """Test that training metadata survives save and retrieve."""
        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, sample_snapshot_with_cutoff)
        db_session.commit()
        db_session.refresh(portfolio)

        service = PortfolioPersistenceService()
        detail = service.get_portfolio(db_session, portfolio.id, user.id)

        assert detail is not None
        assert detail["training_cutoff_date"] == "2026-07-15"
        assert detail["training_draw_count"] == 100


class TestPortfolioEvaluation:
    """Tests for portfolio evaluation service."""

    def test_null_cutoff_rejected(self, db_session, user):
        """Test that NULL training_cutoff_date is rejected."""
        snapshot = {
            "game": "6/49",
            "portfolio_size": 1,
            "selected_tickets": [{"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]}],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [{"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}],
            "structural_optimizer_score": 0.85,
            "structural_optimizer_metrics": {"score": 0.85},
            "version": "1.0.0"
        }

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        eval_service = PortfolioEvaluationService(db_session)
        with pytest.raises(ValueError, match="lacks verified training boundary metadata"):
            eval_service.evaluate_portfolio(portfolio)

    def test_draw_before_cutoff_excluded(self, db_session, user):
        """Test that draws before cutoff are excluded."""
        cutoff = date(2026, 7, 15)

        snapshot = {
            "game": "6/49",
            "portfolio_size": 1,
            "selected_tickets": [{"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]}],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [{"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}],
            "structural_optimizer_score": 0.85,
            "structural_optimizer_metrics": {"score": 0.85},
            "version": "1.0.0",
            "training_cutoff_date": cutoff.isoformat(),
            "training_draw_count": 100
        }

        for days in [-5, -1, 0, 1, 5]:
            draw = Draw(
                draw_date=cutoff + timedelta(days=days),
                numbers=[1, 2, 3, 4, 5, 6],
                lottery_type="6/49"
            )
            db_session.add(draw)
        db_session.commit()

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        eval_service = PortfolioEvaluationService(db_session)
        result = eval_service.evaluate_portfolio(portfolio)

        # Only draws after cutoff should be counted (days 1 and 5)
        assert result.evaluated_draw_count == 2

    def test_draw_equal_to_cutoff_excluded(self, db_session, user):
        """Test that draw exactly on cutoff is excluded."""
        cutoff = date(2026, 7, 15)

        snapshot = {
            "game": "6/49",
            "portfolio_size": 1,
            "selected_tickets": [{"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]}],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [{"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}],
            "structural_optimizer_score": 0.85,
            "structural_optimizer_metrics": {"score": 0.85},
            "version": "1.0.0",
            "training_cutoff_date": cutoff.isoformat(),
            "training_draw_count": 100
        }

        draw = Draw(
            draw_date=cutoff,
            numbers=[1, 2, 3, 4, 5, 6],
            lottery_type="6/49"
        )
        db_session.add(draw)

        draw2 = Draw(
            draw_date=cutoff + timedelta(days=1),
            numbers=[1, 2, 3, 4, 5, 6],
            lottery_type="6/49"
        )
        db_session.add(draw2)
        db_session.commit()

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        eval_service = PortfolioEvaluationService(db_session)
        result = eval_service.evaluate_portfolio(portfolio)

        # Only draw after cutoff should be included
        assert result.evaluated_draw_count == 1
        assert date.fromisoformat(result.date_range[0]) == cutoff + timedelta(days=1)

    def test_wrong_game_draws_excluded(self, db_session, user):
        """Test that draws from other games are excluded."""
        cutoff = date(2026, 7, 15)

        snapshot = {
            "game": "6/49",
            "portfolio_size": 1,
            "selected_tickets": [{"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]}],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [{"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}],
            "structural_optimizer_score": 0.85,
            "structural_optimizer_metrics": {"score": 0.85},
            "version": "1.0.0",
            "training_cutoff_date": cutoff.isoformat(),
            "training_draw_count": 100
        }

        draw1 = Draw(
            draw_date=cutoff + timedelta(days=1),
            numbers=[1, 2, 3, 4, 5, 6],
            lottery_type="6/49"
        )
        db_session.add(draw1)

        draw2 = Draw(
            draw_date=cutoff + timedelta(days=1),
            numbers=[1, 2, 3, 4, 5],
            lottery_type="Daily Grand"
        )
        db_session.add(draw2)
        db_session.commit()

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        eval_service = PortfolioEvaluationService(db_session)
        result = eval_service.evaluate_portfolio(portfolio)

        # Only Lotto 6/49 draw should be included
        assert result.evaluated_draw_count == 1
        assert result.game == "6/49"

    def test_deterministic_ordering(self, db_session, user):
        """Test that draws are ordered by draw_date ASC, id ASC."""
        cutoff = date(2026, 7, 15)

        snapshot = {
            "game": "6/49",
            "portfolio_size": 1,
            "selected_tickets": [{"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]}],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [{"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}],
            "structural_optimizer_score": 0.85,
            "structural_optimizer_metrics": {"score": 0.85},
            "version": "1.0.0",
            "training_cutoff_date": cutoff.isoformat(),
            "training_draw_count": 100
        }

        dates = [cutoff + timedelta(days=d) for d in [3, 1, 2]]
        for d in dates:
            draw = Draw(
                draw_date=d,
                numbers=[1, 2, 3, 4, 5, 6],
                lottery_type="6/49"
            )
            db_session.add(draw)
        db_session.commit()

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        eval_service = PortfolioEvaluationService(db_session)
        result = eval_service.evaluate_portfolio(portfolio)

        # Should be ordered by date: day 1, day 2, day 3
        assert result.evaluated_draw_count == 3
        expected_dates = sorted([cutoff + timedelta(days=d) for d in [1, 2, 3]])
        for i, expected in enumerate(expected_dates):
            assert date.fromisoformat(result.draw_results[i].draw_date) == expected

    def test_lotto649_matching_correct(self, db_session, user):
        """Test Lotto 6/49 match counting is correct."""
        cutoff = date(2026, 7, 15)

        snapshot = {
            "game": "6/49",
            "portfolio_size": 1,
            "selected_tickets": [
                {"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]}
            ],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [{"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}],
            "structural_optimizer_score": 0.85,
            "structural_optimizer_metrics": {"score": 0.85},
            "version": "1.0.0",
            "training_cutoff_date": cutoff.isoformat(),
            "training_draw_count": 100
        }

        draw = Draw(
            draw_date=cutoff + timedelta(days=1),
            numbers=[1, 2, 3, 7, 8, 9],
            lottery_type="6/49"
        )
        db_session.add(draw)
        db_session.commit()

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        eval_service = PortfolioEvaluationService(db_session)
        result = eval_service.evaluate_portfolio(portfolio)

        # Should have 3 matches (1,2,3 match)
        assert result.match_distribution.get(3, 0) == 1

    def test_daily_grand_main_number_matching(self, db_session, user):
        """Test Daily Grand main-number matching is correct."""
        cutoff = date(2026, 7, 15)

        snapshot = {
            "game": "Daily Grand",
            "portfolio_size": 1,
            "selected_tickets": [
                {"numbers": [1, 2, 3, 4, 5], "grand_number": 7, "strategy_ids": [1], "strategy_names": ["Random"]}
            ],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [{"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}],
            "structural_optimizer_score": 0.75,
            "structural_optimizer_metrics": {"score": 0.75},
            "version": "1.0.0",
            "training_cutoff_date": cutoff.isoformat(),
            "training_draw_count": 100
        }

        # Draw: main numbers are first 5, bonus is grand
        draw = Draw(
            draw_date=cutoff + timedelta(days=1),
            numbers=[1, 2, 3, 6, 7, 5],  # main: [1,2,3,6,7], grand: 5
            bonus=5,
            lottery_type="Daily Grand"
        )
        db_session.add(draw)
        db_session.commit()

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        eval_service = PortfolioEvaluationService(db_session)
        result = eval_service.evaluate_portfolio(portfolio)

        # Should have 3 main matches (1,2,3)
        assert result.match_distribution.get(3, 0) == 1
        # Grand number should NOT match (ticket has 7, draw has 5)
        assert result.grand_match_distribution.get(1, 0) == 0

    def test_daily_grand_grand_number_matching(self, db_session, user):
        """Test Daily Grand Grand Number matching is separate."""
        cutoff = date(2026, 7, 15)

        snapshot = {
            "game": "Daily Grand",
            "portfolio_size": 1,
            "selected_tickets": [
                {"numbers": [1, 2, 3, 4, 5], "grand_number": 7, "strategy_ids": [1], "strategy_names": ["Random"]}
            ],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [{"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}],
            "structural_optimizer_score": 0.75,
            "structural_optimizer_metrics": {"score": 0.75},
            "version": "1.0.0",
            "training_cutoff_date": cutoff.isoformat(),
            "training_draw_count": 100
        }

        # Draw with matching grand number
        draw = Draw(
            draw_date=cutoff + timedelta(days=1),
            numbers=[1, 2, 3, 6, 7, 5],
            bonus=7,  # Grand number matches ticket's grand number
            lottery_type="Daily Grand"
        )
        db_session.add(draw)
        db_session.commit()

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        eval_service = PortfolioEvaluationService(db_session)
        result = eval_service.evaluate_portfolio(portfolio)

        # Grand match should be tracked separately
        assert result.grand_match_distribution is not None
        assert result.grand_match_distribution.get(1, 0) == 1

    def test_evaluation_does_not_mutate_tickets(self, db_session, user):
        """Test that evaluation does not modify saved tickets."""
        snapshot = {
            "game": "6/49",
            "portfolio_size": 1,
            "selected_tickets": [
                {"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]}
            ],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [{"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}],
            "structural_optimizer_score": 0.85,
            "structural_optimizer_metrics": {"score": 0.85},
            "version": "1.0.0",
            "training_cutoff_date": "2026-07-15",
            "training_draw_count": 100
        }

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        original_numbers = [t.numbers for t in portfolio.tickets]

        eval_service = PortfolioEvaluationService(db_session)
        result = eval_service.evaluate_portfolio(portfolio)

        # Tickets should be unchanged
        assert [t.numbers for t in portfolio.tickets] == original_numbers

    def test_repeated_evaluation_deterministic(self, db_session, user):
        """Test that repeated evaluation produces identical results."""
        cutoff = date(2026, 7, 15)

        snapshot = {
            "game": "6/49",
            "portfolio_size": 1,
            "selected_tickets": [
                {"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]}
            ],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [{"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}],
            "structural_optimizer_score": 0.85,
            "structural_optimizer_metrics": {"score": 0.85},
            "version": "1.0.0",
            "training_cutoff_date": cutoff.isoformat(),
            "training_draw_count": 100
        }

        draw = Draw(
            draw_date=cutoff + timedelta(days=1),
            numbers=[1, 2, 3, 7, 8, 9],
            lottery_type="6/49"
        )
        db_session.add(draw)
        db_session.commit()

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        eval_service = PortfolioEvaluationService(db_session)

        result1 = eval_service.evaluate_portfolio(portfolio)
        result2 = eval_service.evaluate_portfolio(portfolio)

        assert result1.match_distribution == result2.match_distribution
        assert result1.evaluated_draw_count == result2.evaluated_draw_count
        assert result1.date_range == result2.date_range

    def test_zero_eligible_draws_handled(self, db_session, user):
        """Test that zero eligible draws returns empty result."""
        cutoff = date(2026, 7, 15)

        snapshot = {
            "game": "6/49",
            "portfolio_size": 1,
            "selected_tickets": [
                {"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]}
            ],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [{"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}],
            "structural_optimizer_score": 0.85,
            "structural_optimizer_metrics": {"score": 0.85},
            "version": "1.0.0",
            "training_cutoff_date": cutoff.isoformat(),
            "training_draw_count": 100
        }

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        eval_service = PortfolioEvaluationService(db_session)
        result = eval_service.evaluate_portfolio(portfolio)

        assert result.evaluated_draw_count == 0
        assert result.match_distribution == {}
        assert result.date_range == ("", "")

    def test_match_distribution_invariant(self, db_session, user):
        """Test invariant: sum(match_distribution.values()) == total_tickets * evaluated_draw_count"""
        cutoff = date(2026, 7, 15)

        snapshot = {
            "game": "6/49",
            "portfolio_size": 3,
            "selected_tickets": [
                {"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]},
                {"numbers": [7, 8, 9, 10, 11, 12], "grand_number": None, "strategy_ids": [2], "strategy_names": ["Sobol"]},
                {"numbers": [13, 14, 15, 16, 17, 18], "grand_number": None, "strategy_ids": [1, 2], "strategy_names": ["Random", "Sobol"]}
            ],
            "strategy_ids": [1, 2],
            "strategy_names": ["Random", "Sobol"],
            "requested_candidate_count": 30,
            "generated_candidate_count": 30,
            "unique_structural_candidate_count": 30,
            "master_seed": 42,
            "per_strategy_allocations": [
                {"strategy_id": 1, "strategy_name": "Random", "requested": 15, "generated": 15, "derived_seed": 12345},
                {"strategy_id": 2, "strategy_name": "Sobol", "requested": 15, "generated": 15, "derived_seed": 67890}
            ],
            "structural_optimizer_score": 0.85,
            "structural_optimizer_metrics": {"score": 0.85},
            "version": "1.0.0",
            "training_cutoff_date": cutoff.isoformat(),
            "training_draw_count": 100
        }

        for i in range(5):
            draw = Draw(
                draw_date=cutoff + timedelta(days=i+1),
                numbers=[1, 2, 3, 4, 5, 6],
                lottery_type="6/49"
            )
            db_session.add(draw)
        db_session.commit()

        repo = PortfolioPersistenceRepository()
        portfolio = repo.save(db_session, user.id, snapshot)
        db_session.commit()
        db_session.refresh(portfolio)

        eval_service = PortfolioEvaluationService(db_session)
        result = eval_service.evaluate_portfolio(portfolio)

        # Invariant: sum(match_distribution) == total_tickets * evaluated_draw_count
        total_evaluations = sum(result.match_distribution.values())
        expected = result.total_tickets * result.evaluated_draw_count
        assert total_evaluations == expected
