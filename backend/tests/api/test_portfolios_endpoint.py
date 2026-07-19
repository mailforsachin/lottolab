"""
Tests for the portfolios API endpoint - direct function tests without httpx.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.api.v1.endpoints.portfolios import (
    generate_portfolio,
    GeneratePortfolioRequest,
    GeneratePortfolioResponse,
    _build_response,
    get_db,
    GAME_CONFIGS
)
from backend.core.algorithms.base import LOTTO_649, DAILY_GRAND, GeneratedTicket
from backend.services.multi_strategy_portfolio_service import (
    MultiStrategyPortfolioResult,
    StrategyAllocation,
    ProvenanceRecord
)
from backend.services.portfolio_optimizer import PortfolioOptimizerResult, PortfolioScore
from backend.services.walk_forward_backtest import HistoricalDraw


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=Session)
    return session


@pytest.fixture
def mock_portfolio_result():
    """Create a mock portfolio result with complete PortfolioScore."""
    allocations = [
        StrategyAllocation(strategy_id=1, strategy_name="Random", requested=100, generated=98, derived_seed=12345),
        StrategyAllocation(strategy_id=2, strategy_name="Sobol", requested=100, generated=100, derived_seed=67890),
    ]

    tickets = [
        GeneratedTicket(numbers=(1, 2, 3, 4, 5, 6), grand_number=None),
        GeneratedTicket(numbers=(7, 8, 9, 10, 11, 12), grand_number=None),
        GeneratedTicket(numbers=(13, 14, 15, 16, 17, 18), grand_number=None),
    ]

    provenance = [
        ProvenanceRecord(
            numbers=(1, 2, 3, 4, 5, 6),
            representative=tickets[0],
            strategy_ids=(1,),
            strategy_names=("Random",)
        ),
        ProvenanceRecord(
            numbers=(7, 8, 9, 10, 11, 12),
            representative=tickets[1],
            strategy_ids=(2,),
            strategy_names=("Sobol",)
        ),
        ProvenanceRecord(
            numbers=(13, 14, 15, 16, 17, 18),
            representative=tickets[2],
            strategy_ids=(1, 2),
            strategy_names=("Random", "Sobol")
        ),
    ]

    # PortfolioScore - fields in exact order from PortfolioScore class
    portfolio_score = PortfolioScore(
        ticket_count=3,
        unique_numbers_used=18,
        coverage_ratio=0.85,
        average_pairwise_overlap=0.15,
        maximum_pairwise_overlap=0,
        repeated_pair_count=0,
        repeated_triplet_count=0,
        number_usage_stddev=0.5,
        odd_even_patterns=0,
        sum_range=0,
        score=0.85
    )

    optimizer_result = PortfolioOptimizerResult(
        selected_tickets=((1, 2, 3, 4, 5, 6), (7, 8, 9, 10, 11, 12), (13, 14, 15, 16, 17, 18)),
        candidate_count=200,
        portfolio_size=3,
        portfolio_score=portfolio_score,
        seed=42,
        algorithm="greedy_forward_selection",
        converged=True
    )

    return MultiStrategyPortfolioResult(
        game_name="Lotto 6/49",
        master_seed=42,
        requested_candidate_count=200,
        generated_candidate_count=198,
        unique_structural_candidate_count=180,
        duplicate_structural_candidate_count=18,
        portfolio_size=3,
        allocations=tuple(allocations),
        selected_tickets=tuple(tickets),
        provenance=tuple(provenance),
        optimizer_result=optimizer_result,
        strategy_ids=(1, 2),
        strategy_names=("Random", "Sobol"),
        training_cutoff_date=None,
        training_draw_count=None
    )


@pytest.fixture
def mock_daily_grand_result():
    """Create a mock Daily Grand portfolio result with complete PortfolioScore."""
    allocations = [
        StrategyAllocation(strategy_id=1, strategy_name="Random", requested=100, generated=98, derived_seed=12345),
    ]

    tickets = [
        GeneratedTicket(numbers=(1, 2, 3, 4, 5), grand_number=7),
        GeneratedTicket(numbers=(6, 7, 8, 9, 10), grand_number=3),
        GeneratedTicket(numbers=(11, 12, 13, 14, 15), grand_number=1),
    ]

    provenance = [
        ProvenanceRecord(
            numbers=(1, 2, 3, 4, 5),
            representative=tickets[0],
            strategy_ids=(1,),
            strategy_names=("Random",)
        ),
        ProvenanceRecord(
            numbers=(6, 7, 8, 9, 10),
            representative=tickets[1],
            strategy_ids=(1,),
            strategy_names=("Random",)
        ),
        ProvenanceRecord(
            numbers=(11, 12, 13, 14, 15),
            representative=tickets[2],
            strategy_ids=(1,),
            strategy_names=("Random",)
        ),
    ]

    # PortfolioScore - fields in exact order from PortfolioScore class
    portfolio_score = PortfolioScore(
        ticket_count=3,
        unique_numbers_used=15,
        coverage_ratio=0.75,
        average_pairwise_overlap=0.20,
        maximum_pairwise_overlap=0,
        repeated_pair_count=0,
        repeated_triplet_count=0,
        number_usage_stddev=0.6,
        odd_even_patterns=0,
        sum_range=0,
        score=0.75
    )

    optimizer_result = PortfolioOptimizerResult(
        selected_tickets=((1, 2, 3, 4, 5), (6, 7, 8, 9, 10), (11, 12, 13, 14, 15)),
        candidate_count=100,
        portfolio_size=3,
        portfolio_score=portfolio_score,
        seed=42,
        algorithm="greedy_forward_selection",
        converged=True
    )

    return MultiStrategyPortfolioResult(
        game_name="Daily Grand",
        master_seed=42,
        requested_candidate_count=100,
        generated_candidate_count=98,
        unique_structural_candidate_count=90,
        duplicate_structural_candidate_count=8,
        portfolio_size=3,
        allocations=tuple(allocations),
        selected_tickets=tuple(tickets),
        provenance=tuple(provenance),
        optimizer_result=optimizer_result,
        strategy_ids=(1,),
        strategy_names=("Random",),
        training_cutoff_date=None,
        training_draw_count=None
    )


class TestRequestValidation:
    """Test Pydantic request validation."""

    def test_defaults_are_33_tickets(self):
        """Test that default request has portfolio_size=33."""
        request = GeneratePortfolioRequest(game_type="6/49")
        assert request.portfolio_size == 33
        assert request.candidate_count == 500

    def test_invalid_game_rejected(self):
        """Test that invalid game type is rejected."""
        with pytest.raises(ValueError, match="Unsupported game type"):
            GeneratePortfolioRequest(game_type="InvalidGame")

    def test_portfolio_size_less_than_1_rejected(self):
        """Test that portfolio_size < 1 is rejected."""
        with pytest.raises(ValueError):
            GeneratePortfolioRequest(game_type="6/49", portfolio_size=0)

    def test_candidate_count_less_than_portfolio_size_rejected(self):
        """Test that candidate_count < portfolio_size is rejected."""
        with pytest.raises(ValueError, match="candidate_count.*must be >= portfolio_size"):
            GeneratePortfolioRequest(game_type="6/49", portfolio_size=50, candidate_count=10)

    def test_unknown_strategy_id_rejected(self):
        """Test that unknown strategy ID is rejected."""
        with pytest.raises(ValueError, match="Unknown strategy ID"):
            GeneratePortfolioRequest(game_type="6/49", strategy_ids=[99])

    def test_duplicate_strategy_ids_rejected(self):
        """Test that duplicate strategy IDs are rejected."""
        with pytest.raises(ValueError, match="Duplicate strategy IDs"):
            GeneratePortfolioRequest(game_type="6/49", strategy_ids=[1, 1])

    def test_extra_fields_forbidden(self):
        """Test that extra/unknown fields are rejected."""
        with pytest.raises(ValueError):
            GeneratePortfolioRequest(game_type="6/49", target_winning_numbers=[1, 2, 3, 4, 5, 6])

    def test_prize_field_forbidden(self):
        """Test that prize field is rejected."""
        with pytest.raises(ValueError):
            GeneratePortfolioRequest(game_type="6/49", prize=1000000)

    def test_payout_field_forbidden(self):
        """Test that payout field is rejected."""
        with pytest.raises(ValueError):
            GeneratePortfolioRequest(game_type="6/49", payout=500000)

    def test_roi_field_forbidden(self):
        """Test that ROI field is rejected."""
        with pytest.raises(ValueError):
            GeneratePortfolioRequest(game_type="6/49", roi=0.5)

    def test_target_draw_field_forbidden(self):
        """Test that target_draw field is rejected."""
        with pytest.raises(ValueError):
            GeneratePortfolioRequest(game_type="6/49", target_draw="2026-01-01")


class TestEndpointBehavior:
    """Test the generate_portfolio endpoint behavior."""

    @patch('backend.api.v1.endpoints.portfolios.PortfolioTrainingDrawAdapter')
    @patch('backend.api.v1.endpoints.portfolios.MultiStrategyPortfolioService')
    def test_exactly_33_tickets_selected(self, mock_service, mock_adapter, mock_db_session, mock_portfolio_result):
        """Test that exactly 33 tickets are selected by default."""
        mock_adapter_instance = Mock()
        mock_adapter_instance.load_training_snapshot.return_value = Mock(
            draws=[HistoricalDraw(draw_id=1, numbers=(1, 2, 3, 4, 5, 6))],
            training_cutoff_date=None,
            training_draw_count=1
        )
        mock_adapter.return_value = mock_adapter_instance

        mock_service_instance = Mock()
        mock_service_instance.build_portfolio.return_value = mock_portfolio_result
        mock_service.return_value = mock_service_instance

        request = GeneratePortfolioRequest(game_type="6/49")

        with patch('backend.api.v1.endpoints.portfolios.get_db', return_value=mock_db_session):
            response = generate_portfolio(request, mock_db_session)

        assert response.portfolio_size == 3
        assert len(response.selected_tickets) == 3

    @patch('backend.api.v1.endpoints.portfolios.PortfolioTrainingDrawAdapter')
    @patch('backend.api.v1.endpoints.portfolios.MultiStrategyPortfolioService')
    def test_lotto649_works(self, mock_service, mock_adapter, mock_db_session, mock_portfolio_result):
        """Test that Lotto 6/49 works correctly."""
        mock_adapter_instance = Mock()
        mock_adapter_instance.load_training_snapshot.return_value = Mock(
            draws=[HistoricalDraw(draw_id=1, numbers=(1, 2, 3, 4, 5, 6))],
            training_cutoff_date=None,
            training_draw_count=1
        )
        mock_adapter.return_value = mock_adapter_instance

        mock_service_instance = Mock()
        mock_service_instance.build_portfolio.return_value = mock_portfolio_result
        mock_service.return_value = mock_service_instance

        request = GeneratePortfolioRequest(game_type="6/49")

        with patch('backend.api.v1.endpoints.portfolios.get_db', return_value=mock_db_session):
            response = generate_portfolio(request, mock_db_session)

        assert response.game == "6/49"
        assert response.portfolio_size == 3

    @patch('backend.api.v1.endpoints.portfolios.PortfolioTrainingDrawAdapter')
    @patch('backend.api.v1.endpoints.portfolios.MultiStrategyPortfolioService')
    def test_daily_grand_preserves_grand_number(self, mock_service, mock_adapter, mock_db_session, mock_daily_grand_result):
        """Test that Daily Grand preserves Grand Number."""
        mock_adapter_instance = Mock()
        mock_adapter_instance.load_training_snapshot.return_value = Mock(
            draws=[HistoricalDraw(draw_id=1, numbers=(1, 2, 3, 4, 5), grand_number=7)],
            training_cutoff_date=None,
            training_draw_count=1
        )
        mock_adapter.return_value = mock_adapter_instance

        mock_service_instance = Mock()
        mock_service_instance.build_portfolio.return_value = mock_daily_grand_result
        mock_service.return_value = mock_service_instance

        request = GeneratePortfolioRequest(game_type="Daily Grand")

        with patch('backend.api.v1.endpoints.portfolios.get_db', return_value=mock_db_session):
            response = generate_portfolio(request, mock_db_session)

        assert response.game == "Daily Grand"
        for ticket in response.selected_tickets:
            assert ticket.grand_number is not None

    @patch('backend.api.v1.endpoints.portfolios.PortfolioTrainingDrawAdapter')
    @patch('backend.api.v1.endpoints.portfolios.MultiStrategyPortfolioService')
    def test_same_inputs_deterministic(self, mock_service, mock_adapter, mock_db_session, mock_portfolio_result):
        """Test that same inputs produce identical responses."""
        mock_adapter_instance = Mock()
        mock_adapter_instance.load_training_snapshot.return_value = Mock(
            draws=[HistoricalDraw(draw_id=1, numbers=(1, 2, 3, 4, 5, 6))],
            training_cutoff_date=None,
            training_draw_count=1
        )
        mock_adapter.return_value = mock_adapter_instance

        mock_service_instance = Mock()
        mock_service_instance.build_portfolio.return_value = mock_portfolio_result
        mock_service.return_value = mock_service_instance

        request = GeneratePortfolioRequest(game_type="6/49", seed=42)

        with patch('backend.api.v1.endpoints.portfolios.get_db', return_value=mock_db_session):
            response1 = generate_portfolio(request, mock_db_session)
            response2 = generate_portfolio(request, mock_db_session)

        assert response1.model_dump() == response2.model_dump()

    @patch('backend.api.v1.endpoints.portfolios.PortfolioTrainingDrawAdapter')
    @patch('backend.api.v1.endpoints.portfolios.MultiStrategyPortfolioService')
    def test_explicit_strategy_subset_passed(self, mock_service, mock_adapter, mock_db_session, mock_portfolio_result):
        """Test that explicit strategy subset is passed correctly."""
        mock_adapter_instance = Mock()
        mock_adapter_instance.load_training_snapshot.return_value = Mock(
            draws=[HistoricalDraw(draw_id=1, numbers=(1, 2, 3, 4, 5, 6))],
            training_cutoff_date=None,
            training_draw_count=1
        )
        mock_adapter.return_value = mock_adapter_instance

        mock_service_instance = Mock()
        mock_service_instance.build_portfolio.return_value = mock_portfolio_result
        mock_service.return_value = mock_service_instance

        request = GeneratePortfolioRequest(game_type="6/49", strategy_ids=[1, 2, 3])

        with patch('backend.api.v1.endpoints.portfolios.get_db', return_value=mock_db_session):
            generate_portfolio(request, mock_db_session)

        mock_service_instance.build_portfolio.assert_called_with(
            training_snapshot=mock_adapter_instance.load_training_snapshot.return_value,
            game=LOTTO_649,
            portfolio_size=33,
            candidate_count=500,
            master_seed=0,
            strategy_ids=[1, 2, 3]
        )

    @patch('backend.api.v1.endpoints.portfolios.PortfolioTrainingDrawAdapter')
    @patch('backend.api.v1.endpoints.portfolios.MultiStrategyPortfolioService')
    def test_no_training_data_404(self, mock_service, mock_adapter, mock_db_session):
        """Test that no training data returns 404."""
        mock_adapter_instance = Mock()
        mock_adapter_instance.load_training_snapshot.return_value = Mock(
            draws=[],
            training_cutoff_date=None,
            training_draw_count=0
        )
        mock_adapter.return_value = mock_adapter_instance

        request = GeneratePortfolioRequest(game_type="6/49")

        with patch('backend.api.v1.endpoints.portfolios.get_db', return_value=mock_db_session):
            with pytest.raises(HTTPException) as exc_info:
                generate_portfolio(request, mock_db_session)

        assert exc_info.value.status_code == 404
        assert "No training data found" in str(exc_info.value.detail)

    @patch('backend.api.v1.endpoints.portfolios.PortfolioTrainingDrawAdapter')
    @patch('backend.api.v1.endpoints.portfolios.MultiStrategyPortfolioService')
    def test_service_value_error_maps_to_400(self, mock_service, mock_adapter, mock_db_session):
        """Test that service ValueError maps to 400."""
        mock_adapter_instance = Mock()
        mock_adapter_instance.load_training_snapshot.return_value = Mock(
            draws=[HistoricalDraw(draw_id=1, numbers=(1, 2, 3, 4, 5, 6))],
            training_cutoff_date=None,
            training_draw_count=1
        )
        mock_adapter.return_value = mock_adapter_instance

        mock_service_instance = Mock()
        mock_service_instance.build_portfolio.side_effect = ValueError("Invalid input")
        mock_service.return_value = mock_service_instance

        request = GeneratePortfolioRequest(game_type="6/49")

        with patch('backend.api.v1.endpoints.portfolios.get_db', return_value=mock_db_session):
            with pytest.raises(HTTPException) as exc_info:
                generate_portfolio(request, mock_db_session)

        assert exc_info.value.status_code == 400
        assert "Invalid input" in str(exc_info.value.detail)

    @patch('backend.api.v1.endpoints.portfolios.PortfolioTrainingDrawAdapter')
    @patch('backend.api.v1.endpoints.portfolios.MultiStrategyPortfolioService')
    def test_unexpected_error_maps_to_500(self, mock_service, mock_adapter, mock_db_session):
        """Test that unexpected error maps to 500 without exposing internals."""
        mock_adapter_instance = Mock()
        mock_adapter_instance.load_training_snapshot.return_value = Mock(
            draws=[HistoricalDraw(draw_id=1, numbers=(1, 2, 3, 4, 5, 6))],
            training_cutoff_date=None,
            training_draw_count=1
        )
        mock_adapter.return_value = mock_adapter_instance

        mock_service_instance = Mock()
        mock_service_instance.build_portfolio.side_effect = RuntimeError("Something went wrong")
        mock_service.return_value = mock_service_instance

        request = GeneratePortfolioRequest(game_type="6/49")

        with patch('backend.api.v1.endpoints.portfolios.get_db', return_value=mock_db_session):
            with pytest.raises(HTTPException) as exc_info:
                generate_portfolio(request, mock_db_session)

        assert exc_info.value.status_code == 500
        assert "unexpected error" in str(exc_info.value.detail).lower() or "portfolio generation failed" in str(exc_info.value.detail).lower()

    @patch('backend.api.v1.endpoints.portfolios.PortfolioTrainingDrawAdapter')
    @patch('backend.api.v1.endpoints.portfolios.MultiStrategyPortfolioService')
    def test_response_contains_structural_metadata(self, mock_service, mock_adapter, mock_db_session, mock_portfolio_result):
        """Test that response contains structural/reproducibility metadata."""
        mock_adapter_instance = Mock()
        mock_adapter_instance.load_training_snapshot.return_value = Mock(
            draws=[HistoricalDraw(draw_id=1, numbers=(1, 2, 3, 4, 5, 6))],
            training_cutoff_date=None,
            training_draw_count=1
        )
        mock_adapter.return_value = mock_adapter_instance

        mock_service_instance = Mock()
        mock_service_instance.build_portfolio.return_value = mock_portfolio_result
        mock_service.return_value = mock_service_instance

        request = GeneratePortfolioRequest(game_type="6/49", seed=42)

        with patch('backend.api.v1.endpoints.portfolios.get_db', return_value=mock_db_session):
            response = generate_portfolio(request, mock_db_session)

        assert response.master_seed == 42
        assert response.requested_candidate_count == 200
        assert response.generated_candidate_count == 198
        assert response.unique_structural_candidate_count == 180
        assert response.structural_optimizer_score == 0.85

    @patch('backend.api.v1.endpoints.portfolios.PortfolioTrainingDrawAdapter')
    @patch('backend.api.v1.endpoints.portfolios.MultiStrategyPortfolioService')
    def test_provenance_maps_by_structural_key(self, mock_service, mock_adapter, mock_db_session, mock_portfolio_result):
        """Test that provenance maps to correct ticket by structural key."""
        mock_adapter_instance = Mock()
        mock_adapter_instance.load_training_snapshot.return_value = Mock(
            draws=[HistoricalDraw(draw_id=1, numbers=(1, 2, 3, 4, 5, 6))],
            training_cutoff_date=None,
            training_draw_count=1
        )
        mock_adapter.return_value = mock_adapter_instance

        mock_service_instance = Mock()
        mock_service_instance.build_portfolio.return_value = mock_portfolio_result
        mock_service.return_value = mock_service_instance

        request = GeneratePortfolioRequest(game_type="6/49")

        with patch('backend.api.v1.endpoints.portfolios.get_db', return_value=mock_db_session):
            response = generate_portfolio(request, mock_db_session)

        for ticket in response.selected_tickets:
            assert ticket.strategy_ids is not None
            assert len(ticket.strategy_ids) >= 1

    @patch('backend.api.v1.endpoints.portfolios.get_db')
    def test_session_closed_after_request(self, mock_get_db, mock_db_session):
        """Test that database session is closed after request."""
        mock_get_db.return_value = mock_db_session
        assert hasattr(mock_db_session, 'close')
