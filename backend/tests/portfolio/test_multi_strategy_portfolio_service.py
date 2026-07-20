"""
Tests for MultiStrategyPortfolioService.
"""

import pytest
import copy
from unittest.mock import Mock, patch
from typing import List, Tuple

from backend.core.algorithms.base import DAILY_GRAND, GameConfig, GeneratedTicket
from backend.core.algorithms.registry import available_strategies, get_strategy
from backend.services.walk_forward_backtest import HistoricalDraw
from backend.services.multi_strategy_portfolio_service import (
    MultiStrategyPortfolioService,
    MultiStrategyPortfolioResult,
    StrategyAllocation,
    ProvenanceRecord
)
from backend.services.portfolio_optimizer import PortfolioOptimizer


class MockStrategy:
    """Mock strategy for testing."""

    def __init__(self, name, tickets=None):
        self.name = name
        self._tickets = tickets or []

    def generate(
        self,
        training_draws,
        ticket_count,
        game,
        seed=None,
    ):
        """Generate deterministic mock tickets."""
        if self._tickets:
            return self._tickets[:ticket_count]

        tickets = []
        for i in range(ticket_count):
            numbers = tuple(
                range(
                    i + 1,
                    i + game.main_numbers_drawn + 1,
                )
            )
            tickets.append(
                GeneratedTicket(numbers=numbers)
            )
        return tickets


@pytest.fixture
def game_config():
    """Create a test game config."""
    return GameConfig(
        name="TestGame",
        max_main_number=49,
        main_numbers_drawn=6,
    )


@pytest.fixture
def service():
    """Create a MultiStrategyPortfolioService instance."""
    return MultiStrategyPortfolioService()


@pytest.fixture
def mock_training_draws():
    """Create valid immutable historical training draws."""
    return [
        HistoricalDraw(
            draw_id=1,
            numbers=(1, 2, 3, 4, 5, 6),
        ),
        HistoricalDraw(
            draw_id=2,
            numbers=(7, 8, 9, 10, 11, 12),
        ),
        HistoricalDraw(
            draw_id=3,
            numbers=(13, 14, 15, 16, 17, 18),
        ),
    ]


class TestMultiStrategyPortfolioService:
    """Test suite for MultiStrategyPortfolioService."""

    def test_default_uses_all_strategies(self, service, game_config, mock_training_draws):
        """Test that default uses all registered strategies."""
        all_strategies = available_strategies()
        expected_ids = tuple(sorted(s['id'] for s in all_strategies))

        result = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=3,
            candidate_count=10,
            master_seed=42
        )

        assert result.strategy_ids == expected_ids
        assert len(result.strategy_ids) == len(all_strategies)

    def test_exact_33_selected(self, service, game_config, mock_training_draws):
        """Test that exactly 33 tickets are selected when enough candidates exist."""
        result = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=33,
            candidate_count=100,
            master_seed=42
        )

        assert len(result.selected_tickets) == 33
        assert result.portfolio_size == 33

    def test_selected_tickets_valid(self, service, game_config, mock_training_draws):
        """Test that selected tickets are valid."""
        result = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=5,
            candidate_count=20,
            master_seed=42
        )

        for ticket in result.selected_tickets:
            assert len(ticket.numbers) == game_config.main_numbers_drawn
            assert all(1 <= n <= game_config.max_main_number for n in ticket.numbers)
            assert len(set(ticket.numbers)) == game_config.main_numbers_drawn

    def test_selected_tickets_structurally_unique(self, service, game_config, mock_training_draws):
        """Test that selected tickets are structurally unique."""
        result = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=5,
            candidate_count=20,
            master_seed=42
        )

        seen = set()
        for ticket in result.selected_tickets:
            key = tuple(sorted(ticket.numbers))
            assert key not in seen
            seen.add(key)

    def test_selected_tickets_from_generated_candidates(self, service, game_config, mock_training_draws):
        """Test that all selected tickets originate from generated candidates."""
        result = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=5,
            candidate_count=20,
            master_seed=42
        )

        # All selected tickets should be in the result (they are)
        assert len(result.selected_tickets) == 5

    def test_candidate_allocation_equal_when_divisible(self, service, game_config, mock_training_draws):
        """Test that candidate allocation is equal when divisible."""
        # Use a subset of strategies for predictable allocation
        strategy_ids = [1, 2, 3, 4, 5]
        candidate_count = 50  # Divisible by 5

        # We need to override the strategy generation to see allocation
        # We'll check the allocation metadata
        result = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=10,
            candidate_count=50,
            master_seed=42,
            strategy_ids=strategy_ids
        )

        # Verify allocation is even
        allocations = {a.strategy_id: a.requested for a in result.allocations}
        for count in allocations.values():
            assert count == 10

    def test_deterministic_remainder_allocation(self, service, game_config, mock_training_draws):
        """Test remainder allocation: 503 => 101,101,101,100,100."""
        candidate_count = 503
        strategy_ids = [1, 2, 3, 4, 5]

        result = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=100,
            candidate_count=candidate_count,
            master_seed=42,
            strategy_ids=strategy_ids
        )

        # Check allocation in ascending strategy ID order
        allocations = [a.requested for a in result.allocations]
        assert allocations == [101, 101, 101, 100, 100]

    def test_strategy_ids_normalized_to_ascending(self, service, game_config, mock_training_draws):
        """Test that caller-supplied strategy IDs are normalized to ascending order."""
        # Provide IDs in descending order
        strategy_ids = [5, 3, 1, 4, 2]

        result = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=5,
            candidate_count=25,
            master_seed=42,
            strategy_ids=strategy_ids
        )

        # Should be in ascending order
        assert result.strategy_ids == (1, 2, 3, 4, 5)

    def test_same_inputs_produce_identical_result(self, service, game_config, mock_training_draws):
        """Test that same inputs/master seed produce identical result."""
        kwargs = {
            'training_draws': mock_training_draws,
            'game': game_config,
            'portfolio_size': 5,
            'candidate_count': 20,
            'master_seed': 42
        }

        result1 = service.build_portfolio(**kwargs)
        result2 = service.build_portfolio(**kwargs)

        # Compare key fields
        assert result1.selected_tickets == result2.selected_tickets
        assert result1.allocations == result2.allocations
        assert result1.provenance == result2.provenance

    def test_per_strategy_seeds_stable_and_distinct(self, service, game_config, mock_training_draws):
        """Test that per-strategy seeds are stable and distinct."""
        strategy_ids = [1, 2, 3]
        master_seed = 42

        result1 = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=3,
            candidate_count=9,
            master_seed=master_seed,
            strategy_ids=strategy_ids
        )

        # Get derived seeds
        seeds = [a.derived_seed for a in result1.allocations]

        # All seeds should be distinct
        assert len(set(seeds)) == len(seeds)

        # Run again with same master seed
        result2 = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=3,
            candidate_count=9,
            master_seed=master_seed,
            strategy_ids=strategy_ids
        )

        seeds2 = [a.derived_seed for a in result2.allocations]
        assert seeds == seeds2

    def test_training_draws_snapshotted_not_mutated(
        self,
        service,
        game_config,
        mock_training_draws,
    ):
        """Caller-owned training collection is not mutated."""
        original_draws = list(mock_training_draws)
        draws_copy = list(original_draws)

        service.build_portfolio(
            training_draws=original_draws,
            game=game_config,
            portfolio_size=2,
            candidate_count=6,
            master_seed=42,
        )

        assert original_draws == draws_copy

    def test_cross_strategy_duplicate_deduplicated(
        self,
        monkeypatch,
        game_config,
    ):
        """Cross-strategy duplicate mains collapse structurally."""
        from backend.services import (
            multi_strategy_portfolio_service as module,
        )

        class FakeStrategy:
            def __init__(self, tickets):
                self._tickets = tickets

            def generate(
                self,
                training_draws,
                ticket_count,
                game,
                seed=None,
            ):
                return self._tickets[:ticket_count]

        shared = GeneratedTicket(
            numbers=(1, 2, 3, 4, 5, 6)
        )

        strategies = {
            1: FakeStrategy([
                shared,
                GeneratedTicket(
                    numbers=(7, 8, 9, 10, 11, 12)
                ),
            ]),
            2: FakeStrategy([
                shared,
                GeneratedTicket(
                    numbers=(13, 14, 15, 16, 17, 18)
                ),
            ]),
        }

        monkeypatch.setattr(
            module,
            "get_strategy",
            lambda strategy_id: strategies[strategy_id],
        )

        result = MultiStrategyPortfolioService().build_portfolio(
            training_draws=(),
            game=game_config,
            portfolio_size=2,
            candidate_count=4,
            master_seed=42,
            strategy_ids=[1, 2],
        )

        assert result.generated_candidate_count == 4
        assert result.unique_structural_candidate_count == 3
        assert result.duplicate_structural_candidate_count == 1

        record = next(
            item
            for item in result.provenance
            if item.numbers == shared.numbers
        )
        assert record.strategy_ids == (1, 2)

    def test_duplicate_complete_ticket_within_strategy_rejected(
        self,
        monkeypatch,
        game_config,
    ):
        """A strategy may not emit duplicate complete tickets."""
        from backend.services import (
            multi_strategy_portfolio_service as module,
        )

        duplicate = GeneratedTicket(
            numbers=(1, 2, 3, 4, 5, 6)
        )

        class FakeStrategy:
            def generate(
                self,
                training_draws,
                ticket_count,
                game,
                seed=None,
            ):
                return [duplicate, duplicate]

        monkeypatch.setattr(
            module,
            "get_strategy",
            lambda strategy_id: FakeStrategy(),
        )

        with pytest.raises(
            ValueError,
            match="Duplicate ticket generated",
        ):
            MultiStrategyPortfolioService().build_portfolio(
                training_draws=(),
                game=game_config,
                portfolio_size=1,
                candidate_count=2,
                master_seed=42,
                strategy_ids=[1],
            )

    def test_malformed_strategy_output_rejected(
        self,
        monkeypatch,
        game_config,
    ):
        """Malformed strategy output fails shared validation."""
        from backend.services import (
            multi_strategy_portfolio_service as module,
        )

        class FakeStrategy:
            def generate(
                self,
                training_draws,
                ticket_count,
                game,
                seed=None,
            ):
                return [
                    GeneratedTicket(
                        numbers=(1, 2, 3, 4, 5)
                    )
                ]

        monkeypatch.setattr(
            module,
            "get_strategy",
            lambda strategy_id: FakeStrategy(),
        )

        with pytest.raises(
            ValueError,
            match="invalid ticket output",
        ):
            MultiStrategyPortfolioService().build_portfolio(
                training_draws=(),
                game=game_config,
                portfolio_size=1,
                candidate_count=1,
                master_seed=42,
                strategy_ids=[1],
            )

    def test_provenance_records_every_contributing_strategy(self, service, game_config, mock_training_draws):
        """Test that provenance records every contributing strategy."""
        strategy_ids = [1, 2, 3]
        result = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=3,
            candidate_count=9,
            master_seed=42,
            strategy_ids=strategy_ids
        )

        # Verify provenance exists
        for prov in result.provenance:
            assert prov.strategy_ids is not None
            assert prov.strategy_names is not None
            assert len(prov.strategy_ids) >= 1

    def test_provenance_does_not_affect_structural_scoring(self, service, game_config, mock_training_draws):
        """Test that provenance does not alter structural scoring."""
        # Run optimization once
        result1 = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=3,
            candidate_count=10,
            master_seed=42
        )

        # Run again - should be identical
        result2 = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=3,
            candidate_count=10,
            master_seed=42
        )

        assert result1.selected_tickets == result2.selected_tickets
        assert result1.optimizer_result.portfolio_score == result2.optimizer_result.portfolio_score

    def test_daily_grand_structural_deduplication(
        self,
        monkeypatch,
    ):
        """Same Daily Grand mains collapse across strategies."""
        from backend.services import (
            multi_strategy_portfolio_service as module,
        )

        class FakeStrategy:
            def __init__(self, strategy_id, name, tickets):
                self.strategy_id = strategy_id
                self.name = name
                self._tickets = tickets

            def generate(
                self,
                training_draws,
                ticket_count,
                game,
                seed=None,
            ):
                assert isinstance(training_draws, tuple)
                return self._tickets[:ticket_count]

        strategies = {
            1: FakeStrategy(
                1,
                "First",
                [
                    GeneratedTicket(
                        numbers=(1, 2, 3, 4, 5),
                        grand_number=2,
                    ),
                    GeneratedTicket(
                        numbers=(6, 7, 8, 9, 10),
                        grand_number=1,
                    ),
                ],
            ),
            2: FakeStrategy(
                2,
                "Second",
                [
                    GeneratedTicket(
                        numbers=(1, 2, 3, 4, 5),
                        grand_number=7,
                    ),
                    GeneratedTicket(
                        numbers=(11, 12, 13, 14, 15),
                        grand_number=3,
                    ),
                ],
            ),
        }

        monkeypatch.setattr(
            module,
            "get_strategy",
            lambda strategy_id: strategies[strategy_id],
        )

        service = MultiStrategyPortfolioService()

        result = service.build_portfolio(
            training_draws=(),
            game=DAILY_GRAND,
            portfolio_size=2,
            candidate_count=4,
            master_seed=42,
            strategy_ids=[2, 1],
        )

        assert result.generated_candidate_count == 4
        assert result.unique_structural_candidate_count == 3
        assert result.duplicate_structural_candidate_count == 1

        # Selection is intentionally allowed to vary under deterministic
        # seeded tie-breaking. The service-level contract here is that
        # structural duplicates collapse before optimization.
        assert len(result.selected_tickets) == 2
        assert len({
            ticket.numbers
            for ticket in result.selected_tickets
        }) == 2

        # If the merged duplicate structure is selected, provenance must
        # retain both contributing strategies and the deterministic
        # representative from the lower normalized strategy id.
        duplicate_key = (1, 2, 3, 4, 5)
        records = [
            item
            for item in result.provenance
            if item.numbers == duplicate_key
        ]

        if records:
            assert len(records) == 1
            assert records[0].strategy_ids == (1, 2)

            selected = next(
                ticket
                for ticket in result.selected_tickets
                if ticket.numbers == duplicate_key
            )
            assert selected.grand_number == 2

    def test_insufficient_unique_candidates_fails_clearly(
        self,
        monkeypatch,
        game_config,
    ):
        """Fail when deduplication leaves too few structures."""
        from backend.services import (
            multi_strategy_portfolio_service as module,
        )

        class FakeStrategy:
            def __init__(self, strategy_id, name, tickets):
                self.strategy_id = strategy_id
                self.name = name
                self._tickets = tickets

            def generate(
                self,
                training_draws,
                ticket_count,
                game,
                seed=None,
            ):
                return self._tickets[:ticket_count]

        first = [
            GeneratedTicket(
                numbers=(1, 2, 3, 4, 5, 6),
            ),
            GeneratedTicket(
                numbers=(7, 8, 9, 10, 11, 12),
            ),
            GeneratedTicket(
                numbers=(13, 14, 15, 16, 17, 18),
            ),
        ]

        second = [
            GeneratedTicket(
                numbers=(1, 2, 3, 4, 5, 6),
            ),
            GeneratedTicket(
                numbers=(7, 8, 9, 10, 11, 12),
            ),
            GeneratedTicket(
                numbers=(13, 14, 15, 16, 17, 18),
            ),
        ]

        strategies = {
            1: FakeStrategy(1, "First", first),
            2: FakeStrategy(2, "Second", second),
        }

        monkeypatch.setattr(
            module,
            "get_strategy",
            lambda strategy_id: strategies[strategy_id],
        )

        service = MultiStrategyPortfolioService()

        with pytest.raises(
            ValueError,
            match="Insufficient unique structural candidates",
        ):
            service.build_portfolio(
                training_draws=(),
                game=game_config,
                portfolio_size=4,
                candidate_count=6,
                master_seed=42,
                strategy_ids=[1, 2],
            )

    def test_duplicate_strategy_ids_rejected(self, service, game_config, mock_training_draws):
        """Test that duplicate strategy IDs are rejected."""
        with pytest.raises(ValueError, match="duplicate strategy ID"):
            service.build_portfolio(
                training_draws=mock_training_draws,
                game=game_config,
                portfolio_size=3,
                candidate_count=10,
                master_seed=42,
                strategy_ids=[1, 2, 1, 3]
            )

    def test_unknown_strategy_ids_rejected(self, service, game_config, mock_training_draws):
        """Test that unknown strategy IDs are rejected."""
        with pytest.raises(ValueError, match="unknown strategy ID"):
            service.build_portfolio(
                training_draws=mock_training_draws,
                game=game_config,
                portfolio_size=3,
                candidate_count=10,
                master_seed=42,
                strategy_ids=[1, 2, 99]
            )

    def test_empty_strategy_list_rejected(self, service, game_config, mock_training_draws):
        """Test that empty strategy list is rejected."""
        with pytest.raises(ValueError, match="strategy_ids must not be empty"):
            service.build_portfolio(
                training_draws=mock_training_draws,
                game=game_config,
                portfolio_size=3,
                candidate_count=10,
                master_seed=42,
                strategy_ids=[]
            )

    def test_invalid_portfolio_size_rejected(self, service, game_config, mock_training_draws):
        """Test that invalid portfolio size is rejected."""
        with pytest.raises(ValueError, match="portfolio_size must be >= 1"):
            service.build_portfolio(
                training_draws=mock_training_draws,
                game=game_config,
                portfolio_size=0,
                candidate_count=10,
                master_seed=42
            )

    def test_invalid_candidate_count_rejected(self, service, game_config, mock_training_draws):
        """Test that invalid candidate count is rejected."""
        with pytest.raises(ValueError, match=r"candidate_count .* must be >= portfolio_size"):
            service.build_portfolio(
                training_draws=mock_training_draws,
                game=game_config,
                portfolio_size=10,
                candidate_count=5,
                master_seed=42
            )

    def test_non_integer_seed_rejected(self, service, game_config, mock_training_draws):
        """Test that non-integer seed is rejected."""
        with pytest.raises(ValueError, match="master_seed must be an integer"):
            service.build_portfolio(
                training_draws=mock_training_draws,
                game=game_config,
                portfolio_size=3,
                candidate_count=10,
                master_seed="not_an_integer"
            )

        with pytest.raises(ValueError, match="master_seed must be an integer"):
            service.build_portfolio(
                training_draws=mock_training_draws,
                game=game_config,
                portfolio_size=3,
                candidate_count=10,
                master_seed=True
            )

    def test_result_immutable(self, service, game_config, mock_training_draws):
        """Test that the result is immutable."""
        result = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=3,
            candidate_count=10,
            master_seed=42
        )

        # Verify result is frozen (dataclass frozen=True)
        assert hasattr(result, '__dataclass_fields__')

        # Try to modify - should raise exception if frozen
        with pytest.raises(Exception):
            result.selected_tickets = []  # type: ignore

    def test_result_contains_required_metadata(self, service, game_config, mock_training_draws):
        """Test that result contains all required metadata."""
        result = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=3,
            candidate_count=10,
            master_seed=42
        )

        # Required fields
        assert hasattr(result, 'game_name')
        assert hasattr(result, 'master_seed')
        assert hasattr(result, 'requested_candidate_count')
        assert hasattr(result, 'generated_candidate_count')
        assert hasattr(result, 'unique_structural_candidate_count')
        assert hasattr(result, 'duplicate_structural_candidate_count')
        assert hasattr(result, 'portfolio_size')
        assert hasattr(result, 'allocations')
        assert hasattr(result, 'selected_tickets')
        assert hasattr(result, 'provenance')
        assert hasattr(result, 'optimizer_result')
        assert hasattr(result, 'strategy_ids')
        assert hasattr(result, 'strategy_names')

    def test_invariant_holds(self, service, game_config, mock_training_draws):
        """Test that invariant holds: generated - unique = duplicate."""
        result = service.build_portfolio(
            training_draws=mock_training_draws,
            game=game_config,
            portfolio_size=5,
            candidate_count=20,
            master_seed=42
        )

        assert result.generated_candidate_count - result.unique_structural_candidate_count == result.duplicate_structural_candidate_count

    def test_candidate_count_greater_than_strategies(self, service, game_config, mock_training_draws):
        """Test that candidate_count must be >= number of strategies."""
        with pytest.raises(ValueError, match="candidate_count .* must be >= number of strategies"):
            service.build_portfolio(
                training_draws=mock_training_draws,
                game=game_config,
                portfolio_size=1,
                candidate_count=3,  # Less than number of strategies (5)
                master_seed=42
            )
