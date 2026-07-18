"""Regression tests for leakage-safe simulation API."""

from decimal import Decimal

import pytest

from backend.api.v1.endpoints.simulations import (
    DEFAULT_TICKET_COUNT,
    TICKET_PRICE,
    SimulationRequest,
    resolve_game,
)
from backend.core.algorithms.base import (
    DAILY_GRAND,
    LOTTO_649,
)


def test_default_portfolio_is_33_tickets():
    """Default portfolio matches the ~$100 budget model."""
    request = SimulationRequest(
        strategy_id=1,
    )

    assert (
        request.num_tickets
        == DEFAULT_TICKET_COUNT
        == 33
    )

    assert (
        Decimal(request.num_tickets)
        * TICKET_PRICE
        == Decimal("99.00")
    )


@pytest.mark.parametrize(
    ("value", "expected_name"),
    [
        ("6/49", LOTTO_649.name),
        ("649", LOTTO_649.name),
        ("lotto649", LOTTO_649.name),
        ("dailygrand", DAILY_GRAND.name),
        ("Daily Grand", DAILY_GRAND.name),
        ("daily_grand", DAILY_GRAND.name),
    ],
)
def test_resolve_game_accepts_supported_aliases(
    value,
    expected_name,
):
    game = resolve_game(value)

    assert game.name == expected_name


def test_resolve_game_rejects_unknown_game():
    with pytest.raises(
        ValueError,
        match="Unsupported game_type",
    ):
        resolve_game("unknown")


def test_request_rejects_unknown_strategy_id():
    with pytest.raises(Exception):
        SimulationRequest(
            strategy_id=999,
        )


def test_request_defaults_to_walk_forward_budget():
    request = SimulationRequest(
        strategy_id=3,
    )

    assert request.num_tickets == 33
    assert request.target_count == 500
    assert request.game_type == "6/49"


def test_research_cost_is_distinct_from_portfolio_cost():
    """500 targets are research evaluations, not actual spend."""
    ticket_count = 33
    target_count = 500

    portfolio_cost = (
        Decimal(ticket_count)
        * TICKET_PRICE
    )

    hypothetical_research_cost = (
        Decimal(ticket_count)
        * Decimal(target_count)
        * TICKET_PRICE
    )

    assert portfolio_cost == Decimal("99.00")

    assert (
        hypothetical_research_cost
        == Decimal("49500.00")
    )

    assert (
        hypothetical_research_cost
        != portfolio_cost
    )
