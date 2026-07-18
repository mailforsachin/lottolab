#!/usr/bin/env python3
"""Hybrid strategy combining independent generation methods."""

from __future__ import annotations

from typing import Sequence

from backend.core.algorithms.base import (
    GameConfig,
    GeneratedTicket,
    TicketStrategy,
    ensure_unique_tickets,
    validate_generation_request,
)
from backend.core.algorithms.genetic_strategy import GeneticStrategy
from backend.core.algorithms.monte_carlo_strategy import MonteCarloStrategy
from backend.core.algorithms.random_strategy import RandomStrategy
from backend.core.algorithms.sobol_strategy import SobolStrategy
from backend.services.walk_forward_backtest import HistoricalDraw


class HybridStrategy(TicketStrategy):
    """Combine several strategies while preserving portfolio diversity."""

    strategy_id = 5
    name = "Hybrid"

    def generate(
        self,
        training_draws: Sequence[HistoricalDraw],
        ticket_count: int,
        game: GameConfig,
        seed: int | None = None,
    ) -> list[GeneratedTicket]:
        """Generate a mixed-strategy portfolio."""
        validate_generation_request(ticket_count, game)

        strategies = [
            RandomStrategy(),
            SobolStrategy(),
            MonteCarloStrategy(),
            GeneticStrategy(),
        ]

        base = ticket_count // len(strategies)
        remainder = ticket_count % len(strategies)

        selected: list[GeneratedTicket] = []
        seen: set[
            tuple[tuple[int, ...], int | None]
        ] = set()

        for index, strategy in enumerate(strategies):
            count = base + (
                1 if index < remainder else 0
            )

            if count == 0:
                continue

            strategy_seed = (
                None
                if seed is None
                else seed + (index * 10_000)
            )

            generated = strategy.generate(
                training_draws=training_draws,
                ticket_count=count,
                game=game,
                seed=strategy_seed,
            )

            for ticket in generated:
                key = (
                    ticket.numbers,
                    ticket.grand_number,
                )

                if key not in seen:
                    seen.add(key)
                    selected.append(ticket)

        # Extremely unlikely duplicate collisions between strategies
        # are filled using the random control generator.
        fill_attempt = 0

        while len(selected) < ticket_count:
            fill_attempt += 1

            if fill_attempt > 100:
                raise RuntimeError(
                    "Hybrid strategy could not fill unique portfolio."
                )

            filler = RandomStrategy().generate(
                training_draws=training_draws,
                ticket_count=1,
                game=game,
                seed=(
                    None
                    if seed is None
                    else seed + 100_000 + fill_attempt
                ),
            )[0]

            key = (
                filler.numbers,
                filler.grand_number,
            )

            if key not in seen:
                seen.add(key)
                selected.append(filler)

        return ensure_unique_tickets(
            selected,
            ticket_count,
            game,
        )
