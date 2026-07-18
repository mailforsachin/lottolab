#!/usr/bin/env python3
"""Canonical single-draw ticket evaluation for LottoLab.

A ticket is evaluated against exactly one target draw.

This module contains no database writes and deliberately separates
evaluation mechanics from ticket-generation strategies and API logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Sequence

from backend.core.algorithms.base import (
    DAILY_GRAND,
    LOTTO_649,
    GameConfig,
    GeneratedTicket,
)
from backend.services.walk_forward_backtest import HistoricalDraw


@dataclass(frozen=True)
class PrizeRule:
    """Prize associated with one exact match outcome."""

    main_matches: int
    prize: Decimal
    bonus_match: bool | None = None
    grand_match: bool | None = None


@dataclass(frozen=True)
class TicketEvaluation:
    """Immutable result of evaluating one ticket against one draw."""

    target_draw_id: int
    main_matches: int
    bonus_match: bool
    grand_match: bool
    prize: Decimal

    @property
    def is_winner(self) -> bool:
        """Return whether the ticket won a positive prize."""
        return self.prize > Decimal("0")


# These tables preserve the current LottoLab fixed-prize assumptions.
# They are evaluation configuration, not claims about current official
# lottery payout schedules.
LOTTO_649_PRIZE_RULES = (
    PrizeRule(6, Decimal("5000000")),
    PrizeRule(5, Decimal("100000"), bonus_match=True),
    PrizeRule(5, Decimal("1000"), bonus_match=False),
    PrizeRule(4, Decimal("100")),
    PrizeRule(3, Decimal("10")),
    PrizeRule(2, Decimal("5"), bonus_match=True),
)

DAILY_GRAND_PRIZE_RULES = (
    PrizeRule(5, Decimal("7000000"), grand_match=True),
    PrizeRule(5, Decimal("25000"), grand_match=False),
    PrizeRule(4, Decimal("1000"), grand_match=True),
    PrizeRule(4, Decimal("500"), grand_match=False),
    PrizeRule(3, Decimal("100"), grand_match=True),
    PrizeRule(3, Decimal("20"), grand_match=False),
    PrizeRule(2, Decimal("10"), grand_match=True),
    PrizeRule(1, Decimal("4"), grand_match=True),
    PrizeRule(0, Decimal("4"), grand_match=True),
)


def _validate_target_draw(
    target: HistoricalDraw,
    game: GameConfig,
) -> None:
    """Validate target draw structure against game rules."""
    if len(target.numbers) != game.main_numbers_drawn:
        raise ValueError(
            f"Target draw {target.draw_id} has "
            f"{len(target.numbers)} main numbers; "
            f"expected {game.main_numbers_drawn}."
        )

    if len(set(target.numbers)) != len(target.numbers):
        raise ValueError(
            f"Target draw {target.draw_id} contains duplicate numbers."
        )

    for number in target.numbers:
        if not 1 <= number <= game.max_main_number:
            raise ValueError(
                f"Target draw contains out-of-range number: {number}"
            )

    if game.grand_max is not None:
        if target.grand_number is None:
            raise ValueError(
                "Daily Grand target requires a Grand number."
            )

        if not 1 <= target.grand_number <= game.grand_max:
            raise ValueError(
                "Target Grand number is outside valid range."
            )


def _find_prize(
    rules: Sequence[PrizeRule],
    main_matches: int,
    bonus_match: bool,
    grand_match: bool,
) -> Decimal:
    """Return the prize matching one exact outcome."""
    for rule in rules:
        if rule.main_matches != main_matches:
            continue

        if (
            rule.bonus_match is not None
            and rule.bonus_match != bonus_match
        ):
            continue

        if (
            rule.grand_match is not None
            and rule.grand_match != grand_match
        ):
            continue

        return rule.prize

    return Decimal("0")


def evaluate_ticket(
    ticket: GeneratedTicket,
    target: HistoricalDraw,
    game: GameConfig,
    *,
    bonus_number: int | None = None,
) -> TicketEvaluation:
    """Evaluate one ticket against exactly one target draw.

    The same target draw supplies every component of the outcome.
    This prevents combining a main-number result from one historical
    draw with a bonus or Grand result from another draw.
    """
    ticket.validate(game)
    _validate_target_draw(target, game)

    main_matches = len(
        set(ticket.numbers).intersection(target.numbers)
    )

    if game.name == LOTTO_649.name:
        if bonus_number is not None:
            if not 1 <= bonus_number <= game.max_main_number:
                raise ValueError(
                    "Bonus number is outside valid range."
                )

            if bonus_number in target.numbers:
                raise ValueError(
                    "Bonus number cannot duplicate a main draw number."
                )

        bonus_match = (
            bonus_number is not None
            and bonus_number in ticket.numbers
        )

        prize = _find_prize(
            LOTTO_649_PRIZE_RULES,
            main_matches,
            bonus_match,
            False,
        )

        return TicketEvaluation(
            target_draw_id=target.draw_id,
            main_matches=main_matches,
            bonus_match=bonus_match,
            grand_match=False,
            prize=prize,
        )

    if game.name == DAILY_GRAND.name:
        grand_match = (
            ticket.grand_number == target.grand_number
        )

        prize = _find_prize(
            DAILY_GRAND_PRIZE_RULES,
            main_matches,
            False,
            grand_match,
        )

        return TicketEvaluation(
            target_draw_id=target.draw_id,
            main_matches=main_matches,
            bonus_match=False,
            grand_match=grand_match,
            prize=prize,
        )

    raise ValueError(
        f"Unsupported game configuration: {game.name}"
    )
