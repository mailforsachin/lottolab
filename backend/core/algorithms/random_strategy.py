#!/usr/bin/env python3
"""Random Quick Pick baseline strategy."""

from __future__ import annotations

import random
from typing import Sequence

from backend.core.algorithms.base import (
    GameConfig,
    GeneratedTicket,
    TicketStrategy,
    ensure_unique_tickets,
    validate_generation_request,
)
from backend.services.walk_forward_backtest import HistoricalDraw


class RandomStrategy(TicketStrategy):
    """Uniform random ticket generation used as the control baseline."""

    strategy_id = 1
    name = "Random (Quick Pick)"

    def generate(
        self,
        training_draws: Sequence[HistoricalDraw],
        ticket_count: int,
        game: GameConfig,
        seed: int | None = None,
    ) -> list[GeneratedTicket]:
        """Generate uniformly random unique tickets."""
        validate_generation_request(ticket_count, game)

        rng = random.Random(seed)
        tickets: list[GeneratedTicket] = []
        seen: set[tuple[tuple[int, ...], int | None]] = set()

        attempts = 0
        max_attempts = max(10_000, ticket_count * 100)

        while len(tickets) < ticket_count:
            attempts += 1

            if attempts > max_attempts:
                raise RuntimeError(
                    "Unable to generate requested number of unique tickets."
                )

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

            key = (numbers, grand)

            if key in seen:
                continue

            seen.add(key)
            tickets.append(
                GeneratedTicket(
                    numbers=numbers,
                    grand_number=grand,
                )
            )

        return ensure_unique_tickets(
            tickets,
            ticket_count,
            game,
        )
