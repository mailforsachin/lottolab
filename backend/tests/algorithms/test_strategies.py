#!/usr/bin/env python3
"""Unit tests for LottoLab ticket-generation strategies."""

import pytest

from backend.core.algorithms.base import (
    DAILY_GRAND,
    LOTTO_649,
)
from backend.core.algorithms.registry import get_strategy
from backend.services.walk_forward_backtest import HistoricalDraw


def make_training_draws(count=100):
    """Create deterministic synthetic historical draws."""
    draws = []

    for index in range(count):
        start = (index % 40) + 1

        numbers = tuple(
            sorted(
                {
                    ((start + offset - 1) % 49) + 1
                    for offset in range(6)
                }
            )
        )

        if len(numbers) != 6:
            raise AssertionError(
                "Synthetic draw generation failed."
            )

        draws.append(
            HistoricalDraw(
                draw_id=index + 1,
                numbers=numbers,
                grand_number=(index % 7) + 1,
            )
        )

    return draws


@pytest.mark.parametrize(
    "strategy_id",
    [1, 2, 3, 4, 5],
)
def test_lotto649_strategies_generate_valid_unique_tickets(
    strategy_id,
):
    """Every strategy must generate 33 valid unique 6/49 tickets."""
    strategy = get_strategy(strategy_id)

    tickets = strategy.generate(
        training_draws=make_training_draws(),
        ticket_count=33,
        game=LOTTO_649,
        seed=42,
    )

    assert len(tickets) == 33

    keys = {
        (ticket.numbers, ticket.grand_number)
        for ticket in tickets
    }

    assert len(keys) == 33

    for ticket in tickets:
        ticket.validate(LOTTO_649)
        assert len(ticket.numbers) == 6
        assert ticket.grand_number is None


@pytest.mark.parametrize(
    "strategy_id",
    [1, 2, 3, 4, 5],
)
def test_daily_grand_strategies_generate_valid_unique_tickets(
    strategy_id,
):
    """Every strategy must generate valid Daily Grand tickets."""
    strategy = get_strategy(strategy_id)

    tickets = strategy.generate(
        training_draws=make_training_draws(),
        ticket_count=33,
        game=DAILY_GRAND,
        seed=123,
    )

    assert len(tickets) == 33

    keys = {
        (ticket.numbers, ticket.grand_number)
        for ticket in tickets
    }

    assert len(keys) == 33

    for ticket in tickets:
        ticket.validate(DAILY_GRAND)
        assert len(ticket.numbers) == 5
        assert 1 <= ticket.grand_number <= 7


@pytest.mark.parametrize(
    "strategy_id",
    [1, 2, 3, 4, 5],
)
def test_strategies_are_reproducible_with_same_seed(
    strategy_id,
):
    """Identical input and seed must produce identical portfolios."""
    strategy = get_strategy(strategy_id)
    draws = make_training_draws()

    first = strategy.generate(
        draws,
        10,
        LOTTO_649,
        seed=999,
    )

    second = strategy.generate(
        draws,
        10,
        LOTTO_649,
        seed=999,
    )

    assert first == second
