#!/usr/bin/env python3
"""Tests for leakage-safe LottoLab simulation orchestration."""

from decimal import Decimal

import pytest

from backend.core.algorithms.base import (
    DAILY_GRAND,
    LOTTO_649,
)
from backend.services.simulation_service import (
    SimulationService,
    SimulationTarget,
)
from backend.services.walk_forward_backtest import (
    HistoricalDraw,
)


def make_lotto_targets(
    count: int,
) -> list[SimulationTarget]:
    """Create deterministic valid Lotto 6/49 targets."""
    targets = []

    for index in range(count):
        offset = index % 40

        numbers = tuple(
            sorted(
                {
                    ((offset + step) % 49) + 1
                    for step in range(6)
                }
            )
        )

        # The construction above always yields six unique values.
        bonus = (
            ((offset + 10) % 49) + 1
        )

        targets.append(
            SimulationTarget(
                draw=HistoricalDraw(
                    draw_id=index + 1,
                    numbers=numbers,
                ),
                bonus_number=bonus,
            )
        )

    return targets


def make_daily_grand_targets(
    count: int,
) -> list[SimulationTarget]:
    """Create deterministic valid Daily Grand targets."""
    targets = []

    for index in range(count):
        offset = index % 40

        numbers = tuple(
            sorted(
                {
                    ((offset + step) % 49) + 1
                    for step in range(5)
                }
            )
        )

        targets.append(
            SimulationTarget(
                draw=HistoricalDraw(
                    draw_id=index + 1,
                    numbers=numbers,
                    grand_number=(
                        (index % 7) + 1
                    ),
                ),
            )
        )

    return targets


def test_walk_forward_uses_only_prior_draws(
    monkeypatch,
):
    """Target and future draws must never enter training."""
    observed_training_ids = []

    class RecordingStrategy:
        strategy_id = 99
        name = "Recording"

        def generate(
            self,
            training_draws,
            ticket_count,
            game,
            seed=None,
        ):
            observed_training_ids.append(
                [
                    draw.draw_id
                    for draw in training_draws
                ]
            )

            return [
                __import__(
                    "backend.core.algorithms.base",
                    fromlist=["GeneratedTicket"],
                ).GeneratedTicket(
                    numbers=(
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                    )
                )
                for _ in range(ticket_count)
            ]

    monkeypatch.setattr(
        "backend.services.simulation_service."
        "get_strategy",
        lambda strategy_id: RecordingStrategy(),
    )

    service = SimulationService(
        minimum_training_draws=3
    )

    targets = make_lotto_targets(5)

    result = service.run_walk_forward(
        targets=targets,
        strategy_id=99,
        ticket_count=1,
        game=LOTTO_649,
        seed=42,
    )

    assert result.target_count == 2

    assert observed_training_ids[0] == [
        1,
        2,
        3,
    ]

    assert 4 not in observed_training_ids[0]
    assert 5 not in observed_training_ids[0]

    assert observed_training_ids[1] == [
        1,
        2,
        3,
        4,
    ]

    assert 5 not in observed_training_ids[1]


def test_strategy_id_resolves_real_strategy():
    """Registered strategy ID must drive generation."""
    service = SimulationService(
        minimum_training_draws=3
    )

    result = service.run_walk_forward(
        targets=make_lotto_targets(5),
        strategy_id=1,
        ticket_count=3,
        game=LOTTO_649,
        seed=123,
    )

    assert result.strategy_id == 1
    assert result.strategy_name == "Random (Quick Pick)"
    assert result.target_count == 2
    assert result.total_ticket_purchases == 6


def test_unknown_strategy_fails():
    """Unknown strategy IDs must not silently become Random."""
    service = SimulationService(
        minimum_training_draws=3
    )

    with pytest.raises(
        ValueError,
        match="Unknown strategy_id",
    ):
        service.run_walk_forward(
            targets=make_lotto_targets(5),
            strategy_id=999,
            ticket_count=1,
            game=LOTTO_649,
        )


def test_every_ticket_uses_exact_target_draw():
    """Each evaluation must identify its one actual target."""
    service = SimulationService(
        minimum_training_draws=3
    )

    result = service.run_walk_forward(
        targets=make_lotto_targets(6),
        strategy_id=1,
        ticket_count=4,
        game=LOTTO_649,
        seed=7,
    )

    for target_result in result.target_results:
        for item in target_result.tickets:
            assert (
                item.evaluation.target_draw_id
                == target_result.target_draw_id
            )


def test_daily_grand_uses_same_target_grand():
    """Daily Grand evaluation uses target's own Grand Number."""
    service = SimulationService(
        minimum_training_draws=3
    )

    result = service.run_walk_forward(
        targets=make_daily_grand_targets(5),
        strategy_id=1,
        ticket_count=4,
        game=DAILY_GRAND,
        seed=9,
    )

    assert result.target_count == 2

    for target_result in result.target_results:
        assert len(
            target_result.tickets
        ) == 4


def test_lotto_requires_target_bonus():
    """6/49 target cannot omit its same-draw bonus."""
    targets = make_lotto_targets(5)

    targets[4] = SimulationTarget(
        draw=targets[4].draw,
        bonus_number=None,
    )

    service = SimulationService(
        minimum_training_draws=3
    )

    with pytest.raises(
        ValueError,
        match="requires a bonus",
    ):
        service.run_walk_forward(
            targets=targets,
            strategy_id=1,
            ticket_count=1,
            game=LOTTO_649,
        )


def test_daily_grand_requires_target_grand():
    """Daily Grand target cannot omit its Grand Number."""
    targets = make_daily_grand_targets(5)

    targets[4] = SimulationTarget(
        draw=HistoricalDraw(
            draw_id=targets[4].draw.draw_id,
            numbers=targets[4].draw.numbers,
            grand_number=None,
        )
    )

    service = SimulationService(
        minimum_training_draws=3
    )

    with pytest.raises(
        ValueError,
        match="requires a Grand",
    ):
        service.run_walk_forward(
            targets=targets,
            strategy_id=1,
            ticket_count=1,
            game=DAILY_GRAND,
        )


def test_roi_uses_actual_ticket_purchase_count(
    monkeypatch,
):
    """ROI denominator is purchases, never best-ever history."""
    class FixedStrategy:
        strategy_id = 98
        name = "Fixed"

        def generate(
            self,
            training_draws,
            ticket_count,
            game,
            seed=None,
        ):
            from backend.core.algorithms.base import (
                GeneratedTicket,
            )

            return [
                GeneratedTicket(
                    numbers=(
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                    )
                )
                for _ in range(ticket_count)
            ]

    monkeypatch.setattr(
        "backend.services.simulation_service."
        "get_strategy",
        lambda strategy_id: FixedStrategy(),
    )

    targets = [
        SimulationTarget(
            draw=HistoricalDraw(
                draw_id=1,
                numbers=(
                    10,
                    11,
                    12,
                    13,
                    14,
                    15,
                ),
            ),
            bonus_number=16,
        ),
        SimulationTarget(
            draw=HistoricalDraw(
                draw_id=2,
                numbers=(
                    20,
                    21,
                    22,
                    23,
                    24,
                    25,
                ),
            ),
            bonus_number=26,
        ),
        SimulationTarget(
            draw=HistoricalDraw(
                draw_id=3,
                numbers=(
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                ),
            ),
            bonus_number=7,
        ),
    ]

    service = SimulationService(
        minimum_training_draws=2
    )

    result = service.run_walk_forward(
        targets=targets,
        strategy_id=98,
        ticket_count=1,
        game=LOTTO_649,
    )

    assert result.target_count == 1
    assert result.total_ticket_purchases == 1
    assert result.total_won == Decimal(
        "5000000"
    )

    assert result.total_cost(
        Decimal("3")
    ) == Decimal("3")

    assert result.roi(
        Decimal("3")
    ) == (
        (
            Decimal("5000000")
            - Decimal("3")
        )
        / Decimal("3")
        * Decimal("100")
    )


def test_max_targets_uses_latest_eligible_targets():
    """Bounded runs evaluate only latest eligible targets."""
    service = SimulationService(
        minimum_training_draws=3
    )

    result = service.run_walk_forward(
        targets=make_lotto_targets(10),
        strategy_id=1,
        ticket_count=2,
        game=LOTTO_649,
        seed=5,
        max_targets=2,
    )

    assert result.target_count == 2

    assert [
        item.target_draw_id
        for item in result.target_results
    ] == [
        9,
        10,
    ]

    assert [
        item.training_size
        for item in result.target_results
    ] == [
        8,
        9,
    ]


def test_duplicate_draw_ids_rejected():
    """Ambiguous target identity must be rejected."""
    targets = make_lotto_targets(5)

    targets[4] = SimulationTarget(
        draw=HistoricalDraw(
            draw_id=targets[3].draw.draw_id,
            numbers=targets[4].draw.numbers,
        ),
        bonus_number=targets[4].bonus_number,
    )

    service = SimulationService(
        minimum_training_draws=3
    )

    with pytest.raises(
        ValueError,
        match="Duplicate target draw IDs",
    ):
        service.run_walk_forward(
            targets=targets,
            strategy_id=1,
            ticket_count=1,
            game=LOTTO_649,
        )
