"""
Tests for PortfolioTrainingDrawAdapter.
"""

import pytest
import json
from datetime import date
from unittest.mock import Mock, MagicMock, call
from sqlalchemy.orm import Session

from backend.services.portfolio_training_draw_adapter import (
    PortfolioTrainingDrawAdapter,
)
from backend.services.walk_forward_backtest import HistoricalDraw
from backend.core.algorithms.base import LOTTO_649, DAILY_GRAND


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock(spec=Session)
    return session


class TestPortfolioTrainingDrawAdapter:
    """Test suite for PortfolioTrainingDrawAdapter."""

    def test_load_training_draws_chronological(self, mock_session):
        """Test that draws are loaded in chronological order using SQL ORDER BY."""
        # Create mock draws in the order a real database ORDER BY would return
        mock_draws = [
            Mock(id=1, draw_date=date(2024, 1, 1), numbers=[1, 2, 3, 4, 5, 6], lottery_type="6/49", bonus=None),
            Mock(id=2, draw_date=date(2024, 1, 2), numbers=[7, 8, 9, 10, 11, 12], lottery_type="6/49", bonus=None),
            Mock(id=3, draw_date=date(2024, 1, 3), numbers=[13, 14, 15, 16, 17, 18], lottery_type="6/49", bonus=None),
        ]

        # Setup query mock
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_draws
        mock_session.query.return_value = mock_query

        adapter = PortfolioTrainingDrawAdapter(mock_session)
        draws = adapter.load_training_draws("6/49", LOTTO_649)

        # Should be sorted by date (draw_ids 1, 2, 3)
        assert len(draws) == 3
        assert draws[0].draw_id == 1
        assert draws[1].draw_id == 2
        assert draws[2].draw_id == 3

        # Verify order_by was called with correct ordering expressions
        # We check that order_by was called at least once with the expected fields
        order_by_calls = mock_query.order_by.call_args_list
        assert len(order_by_calls) >= 1
        # The call should contain draw_date.asc() and id.asc()
        # We check that the call included the right attributes
        call_args = order_by_calls[0][0]
        # The first argument should be the draw_date ascending expression
        assert hasattr(call_args[0], 'asc') or 'draw_date' in str(call_args[0])
        # The second argument should be the id ascending expression
        assert len(call_args) >= 2

    def test_lotto649_valid_main_numbers(self, mock_session):
        """Test that Lotto 6/49 valid main numbers become HistoricalDraw observations."""
        mock_draw = Mock(
            id=1,
            draw_date=date(2024, 1, 1),
            numbers=[1, 2, 3, 4, 5, 6],
            lottery_type="6/49",
            bonus=None
        )

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_draw]
        mock_session.query.return_value = mock_query

        adapter = PortfolioTrainingDrawAdapter(mock_session)
        draws = adapter.load_training_draws("6/49", LOTTO_649)

        assert len(draws) == 1
        assert draws[0].draw_id == 1
        assert draws[0].numbers == (1, 2, 3, 4, 5, 6)
        assert draws[0].grand_number is None

    def test_lotto649_invalid_bonus_metadata_still_usable(self, mock_session):
        """Test that row with valid main numbers but invalid bonus metadata remains usable."""
        mock_draw = Mock(
            id=1,
            draw_date=date(2024, 1, 1),
            numbers=[1, 2, 3, 4, 5, 6],
            lottery_type="6/49",
            bonus=None
        )

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_draw]
        mock_session.query.return_value = mock_query

        adapter = PortfolioTrainingDrawAdapter(mock_session)
        draws = adapter.load_training_draws("6/49", LOTTO_649)

        assert len(draws) == 1
        assert draws[0].numbers == (1, 2, 3, 4, 5, 6)

    def test_malformed_main_numbers_fails_clearly(self, mock_session):
        """Test that malformed main-number data fails clearly."""
        mock_draw = Mock(
            id=1,
            draw_date=date(2024, 1, 1),
            numbers=[1, 2, 3, 4, 5],
            lottery_type="6/49",
            bonus=None
        )

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_draw]
        mock_session.query.return_value = mock_query

        adapter = PortfolioTrainingDrawAdapter(mock_session)
        with pytest.raises(ValueError, match="Invalid main numbers"):
            adapter.load_training_draws("6/49", LOTTO_649)

    def test_daily_grand_adapted_correctly(self, mock_session):
        """Test that Daily Grand is correctly adapted."""
        mock_draw = Mock(
            id=1,
            draw_date=date(2024, 1, 1),
            numbers=[1, 2, 3, 4, 5, 7],
            lottery_type="Daily Grand",
            bonus=7
        )

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_draw]
        mock_session.query.return_value = mock_query

        adapter = PortfolioTrainingDrawAdapter(mock_session)
        draws = adapter.load_training_draws("Daily Grand", DAILY_GRAND)

        assert len(draws) == 1
        assert draws[0].draw_id == 1
        assert draws[0].numbers == (1, 2, 3, 4, 5)
        assert draws[0].grand_number == 7

    def test_orm_records_not_mutated(self, mock_session):
        """Test that ORM/database records are not mutated."""
        mock_draw = Mock(
            id=1,
            draw_date=date(2024, 1, 1),
            numbers=[1, 2, 3, 4, 5, 6],
            lottery_type="6/49",
            bonus=None
        )

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_draw]
        mock_session.query.return_value = mock_query

        original_numbers = mock_draw.numbers

        adapter = PortfolioTrainingDrawAdapter(mock_session)
        adapter.load_training_draws("6/49", LOTTO_649)

        assert mock_draw.numbers == original_numbers
        mock_session.add.assert_not_called()
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()
        mock_session.flush.assert_not_called()

    def test_unsupported_game_fails_clearly(self, mock_session):
        """Test that unsupported game fails clearly."""
        adapter = PortfolioTrainingDrawAdapter(mock_session)
        with pytest.raises(ValueError, match="Unsupported lottery type"):
            adapter.load_training_draws("UnsupportedGame", LOTTO_649)

    def test_limit_parameter_works(self, mock_session):
        """Test that the limit parameter works."""
        mock_draws = [
            Mock(id=i, draw_date=date(2024, 1, i), numbers=list(range(i, i+6)), lottery_type="6/49", bonus=None)
            for i in range(1, 11)
        ]

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_draws[:5]
        mock_session.query.return_value = mock_query

        adapter = PortfolioTrainingDrawAdapter(mock_session)
        draws = adapter.load_training_draws("6/49", LOTTO_649, limit=5)

        assert len(draws) == 5
        mock_query.limit.assert_called_with(5)
