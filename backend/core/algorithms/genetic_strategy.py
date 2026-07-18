#!/usr/bin/env python3
"""Genetic Algorithm ticket-generation strategy."""

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


class GeneticStrategy(TicketStrategy):
    """Evolve candidate tickets using training-only descriptive features."""

    strategy_id = 4
    name = "Genetic Algorithm"

    def _random_numbers(
        self,
        rng: random.Random,
        game: GameConfig,
    ) -> tuple[int, ...]:
        return tuple(
            sorted(
                rng.sample(
                    range(1, game.max_main_number + 1),
                    game.main_numbers_drawn,
                )
            )
        )

    def _fitness(
        self,
        numbers: tuple[int, ...],
        frequency: Counter,
        max_frequency: int,
        target_sum: float,
        game: GameConfig,
    ) -> float:
        """Score one chromosome without using future outcomes."""
        frequency_score = sum(
            frequency[number] / max_frequency
            for number in numbers
        ) / game.main_numbers_drawn

        sum_score = 1.0 / (
            1.0 + abs(sum(numbers) - target_sum)
        )

        odd_count = sum(number % 2 for number in numbers)

        parity_score = 1.0 / (
            1.0
            + abs(
                odd_count
                - game.main_numbers_drawn / 2
            )
        )

        consecutive_pairs = sum(
            1
            for left, right in zip(numbers, numbers[1:])
            if right == left + 1
        )

        consecutive_score = 1.0 / (
            1.0 + consecutive_pairs
        )

        return (
            0.35 * frequency_score
            + 0.25 * sum_score
            + 0.20 * parity_score
            + 0.20 * consecutive_score
        )

    def _crossover(
        self,
        parent_a: tuple[int, ...],
        parent_b: tuple[int, ...],
        rng: random.Random,
        game: GameConfig,
    ) -> tuple[int, ...]:
        """Create a valid child from two parent tickets."""
        pool = list(set(parent_a).union(parent_b))
        rng.shuffle(pool)

        child = pool[:game.main_numbers_drawn]

        while len(child) < game.main_numbers_drawn:
            candidate = rng.randint(
                1,
                game.max_main_number,
            )

            if candidate not in child:
                child.append(candidate)

        return tuple(sorted(child))

    def _mutate(
        self,
        chromosome: tuple[int, ...],
        rng: random.Random,
        game: GameConfig,
        mutation_rate: float = 0.15,
    ) -> tuple[int, ...]:
        """Randomly replace one gene."""
        values = list(chromosome)

        if rng.random() >= mutation_rate:
            return chromosome

        position = rng.randrange(len(values))

        available = [
            number
            for number in range(
                1,
                game.max_main_number + 1,
            )
            if number not in values
        ]

        values[position] = rng.choice(available)

        return tuple(sorted(values))

    def generate(
        self,
        training_draws: Sequence[HistoricalDraw],
        ticket_count: int,
        game: GameConfig,
        seed: int | None = None,
    ) -> list[GeneratedTicket]:
        """Evolve a reproducible candidate population."""
        validate_generation_request(ticket_count, game)

        rng = random.Random(seed)

        frequency: Counter = Counter()
        historical_sums = []

        for draw in training_draws:
            main = draw.numbers[:game.main_numbers_drawn]

            frequency.update(main)

            if len(main) == game.main_numbers_drawn:
                historical_sums.append(sum(main))

        max_frequency = max(
            frequency.values(),
            default=1,
        )

        target_sum = (
            mean(historical_sums)
            if historical_sums
            else (
                game.main_numbers_drawn
                * (game.max_main_number + 1)
                / 2
            )
        )

        population_size = max(200, ticket_count * 10)
        generations = 60

        population = [
            self._random_numbers(rng, game)
            for _ in range(population_size)
        ]

        for _ in range(generations):
            population = list(set(population))

            ranked = sorted(
                population,
                key=lambda chromosome: self._fitness(
                    chromosome,
                    frequency,
                    max_frequency,
                    target_sum,
                    game,
                ),
                reverse=True,
            )

            elite_count = max(
                20,
                population_size // 5,
            )

            elites = ranked[:elite_count]

            next_population = list(elites)

            while len(next_population) < population_size:
                parent_a = rng.choice(elites)
                parent_b = rng.choice(elites)

                child = self._crossover(
                    parent_a,
                    parent_b,
                    rng,
                    game,
                )

                child = self._mutate(
                    child,
                    rng,
                    game,
                )

                next_population.append(child)

            population = next_population

        ranked = sorted(
            set(population),
            key=lambda chromosome: self._fitness(
                chromosome,
                frequency,
                max_frequency,
                target_sum,
                game,
            ),
            reverse=True,
        )

        selected: list[GeneratedTicket] = []

        for numbers in ranked:
            if selected:
                overlap = max(
                    len(set(numbers).intersection(ticket.numbers))
                    for ticket in selected
                )

                if overlap >= game.main_numbers_drawn - 1:
                    continue

            grand = (
                rng.randint(1, game.grand_max)
                if game.grand_max is not None
                else None
            )

            candidate = GeneratedTicket(
                numbers=numbers,
                grand_number=grand,
            )

            if candidate not in selected:
                selected.append(candidate)

            if len(selected) == ticket_count:
                break

        if len(selected) != ticket_count:
            raise RuntimeError(
                "Genetic strategy could not generate enough "
                "diverse unique tickets."
            )

        return ensure_unique_tickets(
            selected,
            ticket_count,
            game,
        )
