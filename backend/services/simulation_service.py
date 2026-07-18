#!/usr/bin/env python3
"""Leakage-safe simulation orchestration for LottoLab.

This module separates simulation mechanics from FastAPI and database
persistence.

Core invariants:

* Strategies receive only draws occurring before the target draw.
* strategy_id resolves through the canonical strategy registry.
* Every generated ticket is evaluated against exactly one target draw.
* Lotto 6/49 bonus and Daily Grand Grand Number belong to that same target.
* Historical database rows are never modified.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Sequence

from backend.core.algorithms.base import (
    DAILY_GRAND,
    LOTTO_649,
    GameConfig,
    GeneratedTicket,
)
from backend.core.algorithms.registry import get_strategy
from backend.services.ticket_evaluator import (
    TicketEvaluation,
    evaluate_ticket,
)
from backend.services.walk_forward_backtest import HistoricalDraw


@dataclass(frozen=True)
class SimulationTarget:
    """One immutable target used for out-of-sample evaluation."""

    draw: HistoricalDraw
    bonus_number: int | None = None


@dataclass(frozen=True)
class EvaluatedTicket:
    """Generated ticket paired with its single-draw evaluation."""

    ticket: GeneratedTicket
    evaluation: TicketEvaluation


@dataclass(frozen=True)
class TargetSimulationResult:
    """Result of one portfolio evaluated against one unseen target."""

    target_draw_id: int
    training_size: int
    tickets: tuple[EvaluatedTicket, ...]

    @property
    def total_won(self) -> Decimal:
        """Return total prize value for this target portfolio."""
        return sum(
            (
                item.evaluation.prize
                for item in self.tickets
            ),
            Decimal("0"),
        )


@dataclass(frozen=True)
class WalkForwardSimulationResult:
    """Aggregate result for a leakage-safe walk-forward simulation."""

    strategy_id: int
    strategy_name: str
    game_name: str
    ticket_count_per_target: int
    target_results: tuple[TargetSimulationResult, ...]

    @property
    def target_count(self) -> int:
        """Return number of out-of-sample targets evaluated."""
        return len(self.target_results)

    @property
    def total_ticket_purchases(self) -> int:
        """Return actual number of ticket/draw evaluations."""
        return sum(
            len(result.tickets)
            for result in self.target_results
        )

    @property
    def total_won(self) -> Decimal:
        """Return aggregate prize value."""
        return sum(
            (
                result.total_won
                for result in self.target_results
            ),
            Decimal("0"),
        )

    def total_cost(
        self,
        ticket_price: Decimal,
    ) -> Decimal:
        """Return aggregate cost for all ticket purchases."""
        if ticket_price <= Decimal("0"):
            raise ValueError(
                "ticket_price must be positive."
            )

        return (
            Decimal(self.total_ticket_purchases)
            * ticket_price
        )

    def roi(
        self,
        ticket_price: Decimal,
    ) -> Decimal:
        """Return percentage ROI over actual ticket purchases."""
        cost = self.total_cost(ticket_price)

        return (
            (self.total_won - cost)
            / cost
            * Decimal("100")
        )


class SimulationService:
    """Run strategy generation and canonical single-draw evaluation."""

    def __init__(
        self,
        minimum_training_draws: int = 500,
    ) -> None:
        if minimum_training_draws < 1:
            raise ValueError(
                "minimum_training_draws must be at least 1."
            )

        self.minimum_training_draws = (
            minimum_training_draws
        )

    @staticmethod
    def _validate_target(
        target: SimulationTarget,
        game: GameConfig,
    ) -> None:
        """Validate target metadata required by the selected game."""
        if game.name == LOTTO_649.name:
            if target.bonus_number is None:
                raise ValueError(
                    "Lotto 6/49 target requires a bonus number."
                )

            if target.draw.grand_number is not None:
                raise ValueError(
                    "Lotto 6/49 target cannot contain "
                    "a Grand number."
                )

        elif game.name == DAILY_GRAND.name:
            if target.draw.grand_number is None:
                raise ValueError(
                    "Daily Grand target requires a Grand number."
                )

            if target.bonus_number is not None:
                raise ValueError(
                    "Daily Grand target cannot contain "
                    "a Lotto 6/49 bonus number."
                )

        else:
            raise ValueError(
                f"Unsupported game: {game.name}"
            )

    @staticmethod
    def _validate_order(
        targets: Sequence[SimulationTarget],
    ) -> None:
        """Reject duplicate draw identifiers.

        Ordering is supplied by the database adapter. The domain model
        intentionally has no draw_date field, so chronological sorting
        must occur before constructing these targets.
        """
        draw_ids = [
            target.draw.draw_id
            for target in targets
        ]

        if len(draw_ids) != len(set(draw_ids)):
            raise ValueError(
                "Duplicate target draw IDs detected."
            )

    def run_walk_forward(
        self,
        targets: Iterable[SimulationTarget],
        strategy_id: int,
        ticket_count: int,
        game: GameConfig,
        seed: int | None = None,
        max_targets: int | None = None,
    ) -> WalkForwardSimulationResult:
        """Run an expanding-window out-of-sample simulation.

        For each target at index T:

            training = targets[0:T]
            target   = targets[T]

        Only the HistoricalDraw portion of earlier targets is supplied
        to the strategy. The target and all future draws remain hidden.
        """
        if ticket_count < 1:
            raise ValueError(
                "ticket_count must be at least 1."
            )

        if max_targets is not None and max_targets < 1:
            raise ValueError(
                "max_targets must be at least 1."
            )

        ordered_targets = tuple(targets)

        self._validate_order(
            ordered_targets
        )

        if (
            len(ordered_targets)
            <= self.minimum_training_draws
        ):
            raise ValueError(
                "Not enough draws for the requested "
                "training window."
            )

        for target in ordered_targets:
            self._validate_target(
                target,
                game,
            )

        strategy = get_strategy(
            strategy_id
        )

        eligible_indexes = list(
            range(
                self.minimum_training_draws,
                len(ordered_targets),
            )
        )

        if max_targets is not None:
            eligible_indexes = eligible_indexes[
                -max_targets:
            ]

        results: list[
            TargetSimulationResult
        ] = []

        for target_index in eligible_indexes:
            training_draws = tuple(
                item.draw
                for item
                in ordered_targets[:target_index]
            )

            target = ordered_targets[
                target_index
            ]

            target_seed = (
                None
                if seed is None
                else seed + target_index
            )

            generated = strategy.generate(
                training_draws=training_draws,
                ticket_count=ticket_count,
                game=game,
                seed=target_seed,
            )

            if len(generated) != ticket_count:
                raise ValueError(
                    "Strategy generated "
                    f"{len(generated)} tickets; "
                    f"expected {ticket_count}."
                )

            evaluated: list[
                EvaluatedTicket
            ] = []

            for ticket in generated:
                evaluation = evaluate_ticket(
                    ticket=ticket,
                    target=target.draw,
                    game=game,
                    bonus_number=(
                        target.bonus_number
                        if game.name
                        == LOTTO_649.name
                        else None
                    ),
                )

                if (
                    evaluation.target_draw_id
                    != target.draw.draw_id
                ):
                    raise RuntimeError(
                        "Evaluator returned a result "
                        "for the wrong target draw."
                    )

                evaluated.append(
                    EvaluatedTicket(
                        ticket=ticket,
                        evaluation=evaluation,
                    )
                )

            results.append(
                TargetSimulationResult(
                    target_draw_id=(
                        target.draw.draw_id
                    ),
                    training_size=len(
                        training_draws
                    ),
                    tickets=tuple(
                        evaluated
                    ),
                )
            )

        return WalkForwardSimulationResult(
            strategy_id=strategy_id,
            strategy_name=strategy.name,
            game_name=game.name,
            ticket_count_per_target=(
                ticket_count
            ),
            target_results=tuple(results),
        )
