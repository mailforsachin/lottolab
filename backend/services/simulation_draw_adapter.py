#!/usr/bin/env python3
"""Read-only database adapter for leakage-safe simulation draws.

This module converts LottoLab ORM Draw records into immutable
SimulationTarget domain objects.

It never inserts, updates, deletes, or mutates historical Draw rows.
Chronological ordering is explicitly defined by draw_date ASC, id ASC.

Historical rows that have valid main numbers but invalid outcome metadata
(such as a Lotto 6/49 bonus duplicating a main number) are not repaired or
guessed. Such rows are excluded from evaluation targets.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from backend.core.algorithms.base import (
    DAILY_GRAND,
    LOTTO_649,
    GameConfig,
)
from backend.models import Draw
from backend.services.simulation_service import SimulationTarget
from backend.services.walk_forward_backtest import HistoricalDraw


class SimulationDrawAdapter:
    """Load and normalize historical draws for simulation."""

    LOTTERY_TYPE_BY_GAME = {
        LOTTO_649.name: "6/49",
        DAILY_GRAND.name: "Daily Grand",
    }

    @classmethod
    def lottery_type_for_game(
        cls,
        game: GameConfig,
    ) -> str:
        """Return database lottery_type for a supported game."""
        try:
            return cls.LOTTERY_TYPE_BY_GAME[game.name]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported game: {game.name}"
            ) from exc

    @staticmethod
    def _normalize_numbers(
        numbers: Sequence[int],
        expected_count: int,
        draw_id: int,
    ) -> tuple[int, ...]:
        """Validate and normalize main lottery numbers."""
        try:
            normalized = tuple(
                int(number)
                for number in numbers
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Draw {draw_id} contains invalid numbers."
            ) from exc

        if len(normalized) != expected_count:
            raise ValueError(
                f"Draw {draw_id} contains "
                f"{len(normalized)} main numbers; "
                f"expected {expected_count}."
            )

        if len(set(normalized)) != expected_count:
            raise ValueError(
                f"Draw {draw_id} contains duplicate "
                "main numbers."
            )

        if any(
            number < 1 or number > 49
            for number in normalized
        ):
            raise ValueError(
                f"Draw {draw_id} contains a main number "
                "outside 1..49."
            )

        return tuple(sorted(normalized))

    @classmethod
    def from_orm_draw(
        cls,
        draw: Draw,
        game: GameConfig,
    ) -> SimulationTarget:
        """Convert one ORM Draw into a strict immutable target.

        Evaluation targets require complete and internally valid outcome
        metadata. No missing or invalid bonus/Grand value is inferred.
        """
        if draw.id is None:
            raise ValueError(
                "Historical draw must have an ID."
            )

        expected_lottery_type = (
            cls.lottery_type_for_game(game)
        )

        if draw.lottery_type != expected_lottery_type:
            raise ValueError(
                f"Draw {draw.id} has lottery_type "
                f"{draw.lottery_type!r}; expected "
                f"{expected_lottery_type!r}."
            )

        if not isinstance(draw.numbers, list):
            raise ValueError(
                f"Draw {draw.id} numbers must be a list."
            )

        if game.name == LOTTO_649.name:
            main_numbers = cls._normalize_numbers(
                draw.numbers,
                expected_count=6,
                draw_id=draw.id,
            )

            if draw.bonus is None:
                raise ValueError(
                    f"Draw {draw.id} is missing "
                    "its Lotto 6/49 bonus number."
                )

            try:
                bonus_number = int(draw.bonus)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Draw {draw.id} has an invalid "
                    "bonus number."
                ) from exc

            if not 1 <= bonus_number <= 49:
                raise ValueError(
                    f"Draw {draw.id} has a bonus number "
                    "outside 1..49."
                )

            if bonus_number in main_numbers:
                raise ValueError(
                    f"Draw {draw.id} bonus number "
                    "duplicates a main number."
                )

            return SimulationTarget(
                draw=HistoricalDraw(
                    draw_id=draw.id,
                    numbers=main_numbers,
                ),
                bonus_number=bonus_number,
            )

        if game.name == DAILY_GRAND.name:
            if len(draw.numbers) != 6:
                raise ValueError(
                    f"Draw {draw.id} contains "
                    f"{len(draw.numbers)} stored values; "
                    "expected 5 main numbers plus "
                    "1 Grand Number."
                )

            main_numbers = cls._normalize_numbers(
                draw.numbers[:5],
                expected_count=5,
                draw_id=draw.id,
            )

            try:
                grand_number = int(
                    draw.numbers[5]
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Draw {draw.id} has an invalid "
                    "Grand Number."
                ) from exc

            if not 1 <= grand_number <= 7:
                raise ValueError(
                    f"Draw {draw.id} has a Grand Number "
                    "outside 1..7."
                )

            return SimulationTarget(
                draw=HistoricalDraw(
                    draw_id=draw.id,
                    numbers=main_numbers,
                    grand_number=grand_number,
                )
            )

        raise ValueError(
            f"Unsupported game: {game.name}"
        )

    @classmethod
    def _is_known_invalid_target(
        cls,
        draw: Draw,
        game: GameConfig,
    ) -> bool:
        """Return whether outcome metadata makes a row target-ineligible.

        This method intentionally recognizes only narrowly defined outcome
        defects. Structural corruption of main numbers must still fail
        loudly rather than being silently discarded.
        """
        if game.name == LOTTO_649.name:
            if not isinstance(draw.numbers, list):
                return False

            try:
                main_numbers = tuple(
                    int(number)
                    for number in draw.numbers
                )
            except (TypeError, ValueError):
                return False

            if draw.bonus is None:
                return True

            try:
                bonus_number = int(draw.bonus)
            except (TypeError, ValueError):
                return True

            return (
                not 1 <= bonus_number <= 49
                or bonus_number in main_numbers
            )

        return False

    @classmethod
    def load_targets(
        cls,
        session: Session,
        game: GameConfig,
    ) -> tuple[SimulationTarget, ...]:
        """Load valid evaluation targets in deterministic chronology.

        This method performs SELECT operations only.

        Rows with valid historical main numbers but known-invalid target
        metadata are excluded from evaluation rather than repaired. Other
        structural validation errors continue to fail loudly.
        """
        lottery_type = cls.lottery_type_for_game(
            game
        )

        rows = (
            session.query(Draw)
            .filter(
                Draw.lottery_type == lottery_type
            )
            .order_by(
                Draw.draw_date.asc(),
                Draw.id.asc(),
            )
            .all()
        )

        if not rows:
            raise ValueError(
                f"No historical draws found for "
                f"{lottery_type}."
            )

        targets: list[SimulationTarget] = []

        for row in rows:
            if cls._is_known_invalid_target(
                draw=row,
                game=game,
            ):
                continue

            targets.append(
                cls.from_orm_draw(
                    draw=row,
                    game=game,
                )
            )

        if not targets:
            raise ValueError(
                f"No valid evaluation targets found for "
                f"{lottery_type}."
            )

        return tuple(targets)
