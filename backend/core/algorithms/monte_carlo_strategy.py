#!/usr/bin/env python3
"""Monte Carlo candidate-search strategy for LottoLab."""

from __future__ import annotations

from collections import Counter
import random
from statistics import mean
from typing import Sequence

from backend.core.algorithms.base import (
    GameConfig,
    GeneratedTicket,
    TicketStrategy,
    ensure_unique_tickets,
    validate_generation_request,
)
from backend.services.walk_forward_backtest import HistoricalDraw


class MonteCarloStrategy(TicketStrategy):
    """Generate many candidates and select a diverse historical-fit portfolio."""

    strategy_id = 3
    name = "Monte Carlo Optimized"

    @staticmethod
    def _historical_profile(
        training_draws: Sequence[HistoricalDraw],
        game: GameConfig,
    ) -> tuple[Counter, float]:
        """Build descriptive statistics from training data only."""
        frequency: Counter = Counter()

        sums = []

        for draw in training_draws:
            main = draw.numbers[:game.main_numbers_drawn]

            frequency.update(main)

            if len(main) == game.main_numbers_drawn:
                sums.append(sum(main))

        expected_sum = (
            mean(sums)
            if sums
            else (
                game.main_numbers_drawn
                * (game.max_main_number + 1)
                / 2
            )
        )

        return frequency, expected_sum

    def generate(
        self,
        training_draws: Sequence[HistoricalDraw],
        ticket_count: int,
        game: GameConfig,
        seed: int | None = None,
    ) -> list[GeneratedTicket]:
        """Generate tickets using Monte Carlo candidate search."""
        validate_generation_request(ticket_count, game)

        rng = random.Random(seed)

        frequency, expected_sum = self._historical_profile(
            training_draws,
            game,
        )

        max_frequency = max(frequency.values(), default=1)

        candidate_count = max(ticket_count * 100, 3000)
        candidates: dict[
            tuple[tuple[int, ...], int | None],
            float,
        ] = {}

        for _ in range(candidate_count):
            numbers = tuple(
                sorted(
                    rng.sample(
                        range(1, game.max_main_number + 1),
                        game.main_numbers_drawn,
                    )
                )
            )

            grand = (
                rng.randint(1, game.grand_max)
                if game.grand_max is not None
                else None
            )

            frequency_score = sum(
                frequency[number] / max_frequency
                for number in numbers
            ) / game.main_numbers_drawn

            sum_distance = abs(sum(numbers) - expected_sum)
            sum_score = 1.0 / (1.0 + sum_distance)

            odd_count = sum(number % 2 for number in numbers)
            parity_score = 1.0 / (
                1.0
                + abs(
                    odd_count
                    - (game.main_numbers_drawn / 2)
                )
            )

            score = (
                0.40 * frequency_score
                + 0.30 * sum_score
                + 0.30 * parity_score
            )

            candidates[(numbers, grand)] = score

        ranked = sorted(
            candidates.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        selected: list[GeneratedTicket] = []

        for (numbers, grand), base_score in ranked:
            if selected:
                max_overlap = max(
                    len(set(numbers).intersection(ticket.numbers))
                    for ticket in selected
                )
            else:
                max_overlap = 0

            # Avoid creating a portfolio of nearly identical tickets.
            if (
                selected
                and max_overlap
                >= game.main_numbers_drawn - 1
            ):
                continue

            selected.append(
                GeneratedTicket(
                    numbers=numbers,
                    grand_number=grand,
                )
            )

            if len(selected) == ticket_count:
                break

        if len(selected) != ticket_count:
            raise RuntimeError(
                "Monte Carlo strategy could not construct "
                "the requested diverse portfolio."
            )

        return ensure_unique_tickets(
            selected,
            ticket_count,
            game,
        )
