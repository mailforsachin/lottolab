"""Tests for database-independent optimized portfolio construction."""

import pytest

from backend.core.algorithms.base import DAILY_GRAND, LOTTO_649, GeneratedTicket
from backend.core.algorithms.registry import get_strategy
from backend.services.optimized_portfolio_service import OptimizedPortfolioService


def test_builds_default_33_ticket_lotto649_portfolio() -> None:
    result = OptimizedPortfolioService().build(
        training_draws=(),
        strategy_id=1,
        game=LOTTO_649,
        seed=20260718,
    )

    assert result.strategy_name == get_strategy(1).name
    assert result.game_name == LOTTO_649.name
    assert result.candidate_count == 330
    assert result.unique_candidate_count >= 33
    assert result.portfolio_size == 33
    assert len(result.selected_tickets) == 33
    assert len({ticket.numbers for ticket in result.selected_tickets}) == 33
    assert all(ticket.grand_number is None for ticket in result.selected_tickets)
    assert result.optimizer_result.portfolio_score is not None
    assert result.optimizer_result.portfolio_score.ticket_count == 33


def test_same_seed_reproduces_selected_tickets_and_structural_score() -> None:
    service = OptimizedPortfolioService()
    arguments = {
        "training_draws": (),
        "strategy_id": 1,
        "game": LOTTO_649,
        "portfolio_size": 6,
        "candidate_count": 60,
        "seed": 8128,
    }

    first = service.build(**arguments)
    second = service.build(**arguments)

    assert first == second
    assert first.selected_tickets == second.selected_tickets
    assert first.optimizer_result.portfolio_score == second.optimizer_result.portfolio_score


def test_daily_grand_rehydrates_first_grand_number_for_selected_main_numbers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OptimizedPortfolioService()
    generated = [
        GeneratedTicket((1, 2, 3, 4, 5), 1),
        GeneratedTicket((1, 2, 3, 4, 5), 2),
        GeneratedTicket((6, 7, 8, 9, 10), 3),
        GeneratedTicket((11, 12, 13, 14, 15), 4),
        GeneratedTicket((16, 17, 18, 19, 20), 5),
    ]

    class DailyGrandCandidateStrategy:
        name = "Test Daily Grand candidates"

        def generate(self, **_kwargs):
            return generated

    monkeypatch.setattr(
        "backend.services.optimized_portfolio_service.get_strategy",
        lambda _strategy_id: DailyGrandCandidateStrategy(),
    )

    expected_by_numbers = {}
    for ticket in generated:
        expected_by_numbers.setdefault(ticket.numbers, ticket)

    result = service.build(
        training_draws=(),
        strategy_id=5,
        game=DAILY_GRAND,
        portfolio_size=3,
        candidate_count=len(generated),
        seed=991,
    )

    assert len(result.selected_tickets) == 3
    assert all(ticket.grand_number is not None for ticket in result.selected_tickets)
    assert all(
        ticket == expected_by_numbers[ticket.numbers]
        for ticket in result.selected_tickets
    )
    assert result.optimizer_result.portfolio_score is not None
    assert result.optimizer_result.portfolio_score.ticket_count == 3


@pytest.mark.parametrize(
    ("portfolio_size", "candidate_count"),
    [
        (0, 10),
        (5, 4),
    ],
)
def test_rejects_invalid_portfolio_and_candidate_sizes(
    portfolio_size: int,
    candidate_count: int,
) -> None:
    with pytest.raises(ValueError):
        OptimizedPortfolioService().build(
            training_draws=(),
            strategy_id=1,
            game=LOTTO_649,
            portfolio_size=portfolio_size,
            candidate_count=candidate_count,
            seed=1,
        )


def test_rejects_non_integer_seed() -> None:
    with pytest.raises(ValueError, match="seed must be an integer"):
        OptimizedPortfolioService().build(
            training_draws=(),
            strategy_id=1,
            game=LOTTO_649,
            candidate_count=40,
            seed=1.5,  # type: ignore[arg-type]
        )


def test_rejects_unknown_strategy() -> None:
    with pytest.raises(ValueError, match="Unknown strategy_id"):
        OptimizedPortfolioService().build(
            training_draws=(),
            strategy_id=999,
            game=LOTTO_649,
            candidate_count=40,
        )


def test_rejects_candidates_insufficient_after_structural_deduplication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DuplicateMainNumberStrategy:
        name = "Duplicate main-number candidates"

        def generate(self, **_kwargs):
            return [
                GeneratedTicket((1, 2, 3, 4, 5), 1),
                GeneratedTicket((1, 2, 3, 4, 5), 2),
            ]

    monkeypatch.setattr(
        "backend.services.optimized_portfolio_service.get_strategy",
        lambda _strategy_id: DuplicateMainNumberStrategy(),
    )

    with pytest.raises(ValueError, match="Insufficient unique valid candidates"):
        OptimizedPortfolioService().build(
            training_draws=(),
            strategy_id=1,
            game=DAILY_GRAND,
            portfolio_size=2,
            candidate_count=2,
        )


def test_snapshots_caller_training_data_before_strategy_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received_training_draws = None

    class CapturingStrategy:
        name = "Capturing candidates"

        def generate(self, *, training_draws, **_kwargs):
            nonlocal received_training_draws
            received_training_draws = training_draws
            return [
                GeneratedTicket((1, 2, 3, 4, 5, 6)),
                GeneratedTicket((7, 8, 9, 10, 11, 12)),
            ]

    monkeypatch.setattr(
        "backend.services.optimized_portfolio_service.get_strategy",
        lambda _strategy_id: CapturingStrategy(),
    )
    caller_training_draws = [object()]

    OptimizedPortfolioService().build(
        training_draws=caller_training_draws,  # type: ignore[arg-type]
        strategy_id=1,
        game=LOTTO_649,
        portfolio_size=2,
        candidate_count=2,
    )

    assert caller_training_draws == [caller_training_draws[0]]
    assert received_training_draws == tuple(caller_training_draws)
    assert isinstance(received_training_draws, tuple)
