#!/usr/bin/env python3
"""Central strategy registry for LottoLab."""

from __future__ import annotations

from backend.core.algorithms.base import TicketStrategy
from backend.core.algorithms.genetic_strategy import GeneticStrategy
from backend.core.algorithms.hybrid_strategy import HybridStrategy
from backend.core.algorithms.monte_carlo_strategy import MonteCarloStrategy
from backend.core.algorithms.random_strategy import RandomStrategy
from backend.core.algorithms.sobol_strategy import SobolStrategy


_STRATEGIES: dict[int, type[TicketStrategy]] = {
    1: RandomStrategy,
    2: SobolStrategy,
    3: MonteCarloStrategy,
    4: GeneticStrategy,
    5: HybridStrategy,
}


def get_strategy(strategy_id: int) -> TicketStrategy:
    """Return a fresh strategy instance by numeric ID."""
    strategy_class = _STRATEGIES.get(strategy_id)

    if strategy_class is None:
        raise ValueError(
            f"Unknown strategy_id: {strategy_id}"
        )

    return strategy_class()


def available_strategies() -> list[dict]:
    """Return registered strategy metadata."""
    return [
        {
            "id": strategy_id,
            "name": strategy_class.name,
        }
        for strategy_id, strategy_class
        in sorted(_STRATEGIES.items())
    ]
