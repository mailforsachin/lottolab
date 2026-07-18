#!/usr/bin/env python3
"""Sobol low-discrepancy ticket-generation strategy."""

from __future__ import annotations

import math
from typing import Sequence

from scipy.stats import qmc

from backend.core.algorithms.base import (
    GameConfig,
    GeneratedTicket,
    TicketStrategy,
    ensure_unique_tickets,
    validate_generation_request,
)
from backend.services.walk_forward_backtest import HistoricalDraw


class SobolStrategy(TicketStrategy):
    """Generate broadly distributed tickets using a Sobol sequence."""

    strategy_id = 2
    name = "Sobol Sequence"

    def generate(
        self,
        training_draws: Sequence[HistoricalDraw],
        ticket_count: int,
        game: GameConfig,
        seed: int | None = None,
    ) -> list[GeneratedTicket]:
        """Generate unique low-discrepancy ticket combinations."""
        validate_generation_request(ticket_count, game)

        dimension = (
            game.main_numbers_drawn
            + (1 if game.grand_max is not None else 0)
        )

        sampler = qmc.Sobol(
            d=dimension,
            scramble=True,
            seed=seed,
        )

        tickets: list[GeneratedTicket] = []
        seen: set[tuple[tuple[int, ...], int | None]] = set()

        batch_power = max(
            4,
            math.ceil(math.log2(max(ticket_count * 4, 16))),
        )

        attempts = 0

        while len(tickets) < ticket_count:
            attempts += 1

            if attempts > 20:
                raise RuntimeError(
                    "Sobol strategy could not generate enough unique tickets."
                )

            samples = sampler.random_base2(m=batch_power)

            for sample in samples:
                ranked = sorted(
                    range(game.max_main_number),
                    key=lambda index: (
                        sample[
                            index % game.main_numbers_drawn
                        ]
                        + (
                            index
                            / (
                                game.max_main_number
                                * game.main_numbers_drawn
                            )
                        )
                    ),
                )

                numbers = tuple(
                    sorted(
                        index + 1
                        for index in ranked[
                            :game.main_numbers_drawn
                        ]
                    )
                )

                grand = None

                if game.grand_max is not None:
                    grand_value = sample[-1]
                    grand = min(
                        game.grand_max,
                        int(grand_value * game.grand_max) + 1,
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

                if len(tickets) == ticket_count:
                    break

            # random_base2 requires balance constraints across calls.
            # Reinitialize deterministically for another larger batch if needed.
            if len(tickets) < ticket_count:
                batch_power += 1
                sampler = qmc.Sobol(
                    d=dimension,
                    scramble=True,
                    seed=(seed or 0) + attempts,
                )

        return ensure_unique_tickets(
            tickets,
            ticket_count,
            game,
        )
