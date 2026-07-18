#!/usr/bin/env python3
"""Shared contracts and utilities for LottoLab ticket-generation strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

from backend.services.walk_forward_backtest import HistoricalDraw


@dataclass(frozen=True)
class GameConfig:
    """Rules required to generate tickets for one lottery game."""

    name: str
    max_main_number: int
    main_numbers_drawn: int
    grand_max: int | None = None

    def validate(self) -> None:
        """Validate game configuration."""
        if self.max_main_number < 1:
            raise ValueError("max_main_number must be positive.")

        if self.main_numbers_drawn < 1:
            raise ValueError("main_numbers_drawn must be positive.")

        if self.main_numbers_drawn > self.max_main_number:
            raise ValueError(
                "main_numbers_drawn cannot exceed max_main_number."
            )

        if self.grand_max is not None and self.grand_max < 1:
            raise ValueError("grand_max must be positive when supplied.")


LOTTO_649 = GameConfig(
    name="6/49",
    max_main_number=49,
    main_numbers_drawn=6,
)

DAILY_GRAND = GameConfig(
    name="Daily Grand",
    max_main_number=49,
    main_numbers_drawn=5,
    grand_max=7,
)


@dataclass(frozen=True)
class GeneratedTicket:
    """A generated lottery ticket."""

    numbers: tuple[int, ...]
    grand_number: int | None = None

    def validate(self, game: GameConfig) -> None:
        """Validate the ticket against game rules."""
        if len(self.numbers) != game.main_numbers_drawn:
            raise ValueError(
                f"Expected {game.main_numbers_drawn} main numbers; "
                f"received {len(self.numbers)}."
            )

        if len(set(self.numbers)) != len(self.numbers):
            raise ValueError("Ticket contains duplicate main numbers.")

        if tuple(sorted(self.numbers)) != self.numbers:
            raise ValueError("Ticket main numbers must be sorted.")

        for number in self.numbers:
            if not 1 <= number <= game.max_main_number:
                raise ValueError(
                    f"Main number {number} is outside valid range."
                )

        if game.grand_max is None:
            if self.grand_number is not None:
                raise ValueError(
                    "Grand number supplied for a game without one."
                )
        else:
            if self.grand_number is None:
                raise ValueError("Grand number is required.")

            if not 1 <= self.grand_number <= game.grand_max:
                raise ValueError("Grand number is outside valid range.")


class TicketStrategy(ABC):
    """Abstract interface implemented by every LottoLab strategy."""

    strategy_id: int
    name: str

    @abstractmethod
    def generate(
        self,
        training_draws: Sequence[HistoricalDraw],
        ticket_count: int,
        game: GameConfig,
        seed: int | None = None,
    ) -> list[GeneratedTicket]:
        """Generate tickets using only supplied historical training draws."""
        raise NotImplementedError


def validate_generation_request(
    ticket_count: int,
    game: GameConfig,
) -> None:
    """Validate common strategy inputs."""
    game.validate()

    if ticket_count < 1:
        raise ValueError("ticket_count must be at least 1.")


def ensure_unique_tickets(
    tickets: Sequence[GeneratedTicket],
    expected_count: int,
    game: GameConfig,
) -> list[GeneratedTicket]:
    """Validate tickets and reject duplicate complete combinations."""
    if len(tickets) != expected_count:
        raise ValueError(
            f"Expected {expected_count} tickets; received {len(tickets)}."
        )

    seen: set[tuple[tuple[int, ...], int | None]] = set()

    for ticket in tickets:
        ticket.validate(game)

        key = (ticket.numbers, ticket.grand_number)

        if key in seen:
            raise ValueError(f"Duplicate ticket generated: {key}")

        seen.add(key)

    return list(tickets)
