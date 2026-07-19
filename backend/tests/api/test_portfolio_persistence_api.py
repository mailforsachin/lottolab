"""
API-level tests for portfolio persistence endpoints.
Uses the same testing pattern as test_portfolios_endpoint.py - direct function tests without httpx.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.api.v1.endpoints.portfolios import (
    save_portfolio,
    list_portfolios,
    get_portfolio,
    delete_portfolio,
    SavePortfolioRequest,
)
from backend.models.user import User


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=Session)
    return session


@pytest.fixture
def mock_current_user():
    """Create a mock current user."""
    user = User(
        id=1,
        username="test_user",
        hashed_password="hash",
        is_active=True
    )
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


class TestSavePortfolio:
    """Tests for saving portfolios."""

    def test_save_portfolio_succeeds(self, mock_db_session, mock_current_user, sample_snapshot_lotto649):
        """Test that saving a valid portfolio succeeds."""
        with patch('backend.api.v1.endpoints.portfolios.PortfolioPersistenceService') as MockService:
            mock_service = Mock()
            mock_portfolio = Mock()
            mock_portfolio.id = 1
            mock_portfolio.created_at = Mock()
            mock_portfolio.created_at.isoformat.return_value = "2026-07-18T12:00:00"
            mock_portfolio.game_type = "6/49"
            mock_portfolio.portfolio_size = 3
            mock_portfolio.tickets = []
            mock_service.save_portfolio.return_value = mock_portfolio
            MockService.return_value = mock_service

            request = SavePortfolioRequest(**sample_snapshot_lotto649)
            response = save_portfolio(request, mock_current_user, mock_db_session)

            assert response.id == 1
            assert response.game_type == "6/49"
            assert response.portfolio_size == 3

    def test_save_portfolio_ownership_assigned_server_side(self, mock_db_session, mock_current_user, sample_snapshot_lotto649):
        """Test that ownership comes from current_user.id, not request."""
        with patch('backend.api.v1.endpoints.portfolios.PortfolioPersistenceService') as MockService:
            mock_service = Mock()
            mock_portfolio = Mock()
            mock_portfolio.id = 1
            mock_portfolio.created_at = Mock()
            mock_portfolio.created_at.isoformat.return_value = "2026-07-18T12:00:00"
            mock_portfolio.game_type = "6/49"
            mock_portfolio.portfolio_size = 3
            mock_portfolio.tickets = []
            mock_service.save_portfolio.return_value = mock_portfolio
            MockService.return_value = mock_service

            request = SavePortfolioRequest(**sample_snapshot_lotto649)
            save_portfolio(request, mock_current_user, mock_db_session)

            # Use assert_called_once_with to verify keyword arguments
            mock_service.save_portfolio.assert_called_once_with(
                session=mock_db_session,
                user_id=mock_current_user.id,
                snapshot=request.model_dump()
            )

    def test_save_portfolio_user_id_extra_field_rejected(self, sample_snapshot_lotto649):
        """Test that user_id extra field is rejected."""
        bad_snapshot = sample_snapshot_lotto649.copy()
        bad_snapshot["user_id"] = 123

        with pytest.raises(ValueError):
            SavePortfolioRequest(**bad_snapshot)

    def test_save_portfolio_lotto649_with_grand_number_rejected(self, sample_snapshot_lotto649):
        """Test that Lotto 6/49 ticket with grand number is rejected."""
        bad_snapshot = sample_snapshot_lotto649.copy()
        bad_snapshot["selected_tickets"][0]["grand_number"] = 5

        with pytest.raises(ValueError, match="Lotto 6/49 tickets must not have grand_number"):
            SavePortfolioRequest(**bad_snapshot)

    def test_save_portfolio_dailygrand_missing_grand_number_rejected(self):
        """Test that Daily Grand ticket without grand number is rejected."""
        snapshot = {
            "game": "Daily Grand",
            "portfolio_size": 1,
            "selected_tickets": [
                {
                    "numbers": [1, 2, 3, 4, 5],
                    "grand_number": None,
                    "strategy_ids": [1],
                    "strategy_names": ["Random"]
                }
            ],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [
                {"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}
            ],
            "structural_optimizer_score": 0.75,
            "structural_optimizer_metrics": {"score": 0.75},
            "version": "1.0.0"
        }

        with pytest.raises(ValueError, match="Daily Grand ticket must have grand_number"):
            SavePortfolioRequest(**snapshot)

    def test_save_portfolio_dailygrand_invalid_grand_number_rejected(self):
        """Test that Daily Grand with invalid grand number is rejected."""
        snapshot = {
            "game": "Daily Grand",
            "portfolio_size": 1,
            "selected_tickets": [
                {
                    "numbers": [1, 2, 3, 4, 5],
                    "grand_number": 99,
                    "strategy_ids": [1],
                    "strategy_names": ["Random"]
                }
            ],
            "strategy_ids": [1],
            "strategy_names": ["Random"],
            "requested_candidate_count": 10,
            "generated_candidate_count": 10,
            "unique_structural_candidate_count": 10,
            "master_seed": 42,
            "per_strategy_allocations": [
                {"strategy_id": 1, "strategy_name": "Random", "requested": 10, "generated": 10, "derived_seed": 12345}
            ],
            "structural_optimizer_score": 0.75,
            "structural_optimizer_metrics": {"score": 0.75},
            "version": "1.0.0"
        }

        with pytest.raises(ValueError, match="Grand number 99 outside valid range 1-7"):
            SavePortfolioRequest(**snapshot)

    def test_save_portfolio_duplicate_structural_tickets_rejected(self, sample_snapshot_lotto649):
        """Test that duplicate structural tickets are rejected."""
        bad_snapshot = sample_snapshot_lotto649.copy()
        bad_snapshot["selected_tickets"][1]["numbers"] = [1, 2, 3, 4, 5, 6]

        with pytest.raises(ValueError, match="Duplicate structural ticket found"):
            SavePortfolioRequest(**bad_snapshot)

    def test_save_portfolio_wrong_ticket_count_rejected(self, sample_snapshot_lotto649):
        """Test that wrong ticket count is rejected."""
        bad_snapshot = sample_snapshot_lotto649.copy()
        bad_snapshot["portfolio_size"] = 5

        with pytest.raises(ValueError, match="selected_tickets count.*must equal portfolio_size"):
            SavePortfolioRequest(**bad_snapshot)

    def test_save_portfolio_invalid_game_rejected(self, sample_snapshot_lotto649):
        """Test that invalid game is rejected."""
        bad_snapshot = sample_snapshot_lotto649.copy()
        bad_snapshot["game"] = "InvalidGame"

        with pytest.raises(ValueError, match="Unsupported game type"):
            SavePortfolioRequest(**bad_snapshot)


class TestListPortfolios:
    """Tests for listing portfolios."""

    def test_list_portfolios_returns_only_current_user_portfolios(self, mock_db_session, mock_current_user):
        """Test that list returns only the current user's portfolios."""
        with patch('backend.api.v1.endpoints.portfolios.PortfolioPersistenceService') as MockService:
            mock_service = Mock()
            mock_service.list_portfolios.return_value = {
                "portfolios": [
                    {
                        "id": 1,
                        "game_type": "6/49",
                        "portfolio_size": 3,
                        "created_at": "2026-07-18T12:00:00",
                        "structural_score": 0.85
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0
            }
            MockService.return_value = mock_service

            response = list_portfolios(50, 0, mock_current_user, mock_db_session)

            mock_service.list_portfolios.assert_called_once_with(
                session=mock_db_session,
                user_id=mock_current_user.id,
                limit=50,
                offset=0
            )
            assert response.total == 1


class TestGetPortfolio:
    """Tests for getting a portfolio."""

    def test_get_portfolio_succeeds(self, mock_db_session, mock_current_user):
        """Test that getting a portfolio succeeds."""
        with patch('backend.api.v1.endpoints.portfolios.PortfolioPersistenceService') as MockService:
            mock_service = Mock()
            mock_service.get_portfolio.return_value = {
                "id": 1,
                "game": "6/49",
                "portfolio_size": 3,
                "selected_tickets": [
                    {"numbers": [1, 2, 3, 4, 5, 6], "grand_number": None, "strategy_ids": [1], "strategy_names": ["Random"]}
                ],
                "strategy_ids": [1],
                "strategy_names": ["Random"],
                "requested_candidate_count": 10,
                "generated_candidate_count": 10,
                "unique_structural_candidate_count": 10,
                "master_seed": 42,
                "per_strategy_allocations": [],
                "structural_optimizer_score": 0.85,
                "structural_optimizer_metrics": {"score": 0.85},
                "version": "1.0.0",
                "created_at": "2026-07-18T12:00:00"
            }
            MockService.return_value = mock_service

            response = get_portfolio(1, mock_current_user, mock_db_session)

            mock_service.get_portfolio.assert_called_once_with(
                session=mock_db_session,
                portfolio_id=1,
                user_id=mock_current_user.id
            )
            assert response.id == 1

    def test_get_portfolio_wrong_owner_returns_404(self, mock_db_session, mock_current_user):
        """Test that wrong-owner get returns 404 (same as nonexistent)."""
        with patch('backend.api.v1.endpoints.portfolios.PortfolioPersistenceService') as MockService:
            mock_service = Mock()
            mock_service.get_portfolio.return_value = None
            MockService.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                get_portfolio(999, mock_current_user, mock_db_session)

            assert exc_info.value.status_code == 404


class TestDeletePortfolio:
    """Tests for deleting a portfolio."""

    def test_delete_portfolio_succeeds(self, mock_db_session, mock_current_user):
        """Test that deleting a portfolio succeeds (204 semantics)."""
        with patch('backend.api.v1.endpoints.portfolios.PortfolioPersistenceService') as MockService:
            mock_service = Mock()
            mock_service.delete_portfolio.return_value = True
            MockService.return_value = mock_service

            response = delete_portfolio(1, mock_current_user, mock_db_session)

            mock_service.delete_portfolio.assert_called_once_with(
                session=mock_db_session,
                portfolio_id=1,
                user_id=mock_current_user.id
            )
            assert response is None

    def test_delete_portfolio_wrong_owner_returns_404(self, mock_db_session, mock_current_user):
        """Test that wrong-owner delete returns 404 (same as nonexistent)."""
        with patch('backend.api.v1.endpoints.portfolios.PortfolioPersistenceService') as MockService:
            mock_service = Mock()
            mock_service.delete_portfolio.return_value = False
            MockService.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                delete_portfolio(999, mock_current_user, mock_db_session)

            assert exc_info.value.status_code == 404
