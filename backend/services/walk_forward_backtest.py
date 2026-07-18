#!/usr/bin/env python3
"""Leakage-safe walk-forward backtesting utilities for LottoLab.

A strategy may see only draws occurring before the target draw.
This module is deliberately database-independent so it can be unit tested
without modifying LottoLab historical data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence


Ticket = tuple[int, ...]


@dataclass(frozen=True)
class HistoricalDraw:
    """Immutable draw representation used by the backtesting engine."""

    draw_id: int
    numbers: tuple[int, ...]
    grand_number: int | None = None


@dataclass(frozen=True)
class BacktestResult:
    """One out-of-sample prediction result."""

    target_draw_id: int
    training_size: int
    tickets: tuple[Ticket, ...]
    match_counts: tuple[int, ...]


StrategyFunction = Callable[
    [Sequence[HistoricalDraw], int],
    Sequence[Ticket],
]


class WalkForwardBacktester:
    """Run expanding-window out-of-sample strategy evaluation."""

    def __init__(self, minimum_training_draws: int = 500) -> None:
        if minimum_training_draws < 1:
            raise ValueError(
                "minimum_training_draws must be at least 1."
            )

        self.minimum_training_draws = minimum_training_draws

    @staticmethod
    def _validate_ticket(ticket: Sequence[int]) -> Ticket:
        """Normalize and validate a generated ticket."""

        normalized = tuple(sorted(int(number) for number in ticket))

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                f"Ticket contains duplicate numbers: {normalized}"
            )

        return normalized

    @staticmethod
    def _count_matches(
        ticket: Sequence[int],
        actual_numbers: Sequence[int],
    ) -> int:
        """Count matches for exactly one target draw."""

        return len(set(ticket).intersection(actual_numbers))

    def run(
        self,
        draws: Iterable[HistoricalDraw],
        strategy: StrategyFunction,
        ticket_count: int = 33,
    ) -> list[BacktestResult]:
        """Execute an expanding-window walk-forward backtest.

        For target draw at index T:

            training data = draws[0:T]
            target        = draws[T]

        The target draw and all future draws are never passed to strategy().
        """

        ordered_draws = list(draws)

        if ticket_count < 1:
            raise ValueError("ticket_count must be at least 1.")

        if len(ordered_draws) <= self.minimum_training_draws:
            raise ValueError(
                "Not enough draws for the requested training window."
            )

        results: list[BacktestResult] = []

        for target_index in range(
            self.minimum_training_draws,
            len(ordered_draws),
        ):
            training_draws = ordered_draws[:target_index]
            target_draw = ordered_draws[target_index]

            generated = strategy(
                tuple(training_draws),
                ticket_count,
            )

            tickets = tuple(
                self._validate_ticket(ticket)
                for ticket in generated
            )

            if len(tickets) != ticket_count:
                raise ValueError(
                    "Strategy generated "
                    f"{len(tickets)} tickets; "
                    f"expected {ticket_count}."
                )

            matches = tuple(
                self._count_matches(
                    ticket,
                    target_draw.numbers,
                )
                for ticket in tickets
            )

            results.append(
                BacktestResult(
                    target_draw_id=target_draw.draw_id,
                    training_size=len(training_draws),
                    tickets=tickets,
                    match_counts=matches,
                )
            )

        return results
