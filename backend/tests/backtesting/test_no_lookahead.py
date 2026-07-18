#!/usr/bin/env python3
"""Tests proving the backtester does not expose future draws."""

from backend.services.walk_forward_backtest import (
    HistoricalDraw,
    WalkForwardBacktester,
)


def test_strategy_receives_only_draws_before_target():
    """Target and future draws must never enter strategy training data."""

    draws = [
        HistoricalDraw(
            draw_id=i,
            numbers=(1, 2, 3, 4, 5, 6),
        )
        for i in range(1, 11)
    ]

    observed_training_ids = []

    def strategy(training_draws, ticket_count):
        observed_training_ids.append(
            [draw.draw_id for draw in training_draws]
        )

        return [
            (1, 2, 3, 4, 5, 6)
            for _ in range(ticket_count)
        ]

    backtester = WalkForwardBacktester(
        minimum_training_draws=5
    )

    results = backtester.run(
        draws=draws,
        strategy=strategy,
        ticket_count=1,
    )

    assert len(results) == 5

    # Prediction for draw 6 may use only draws 1-5.
    assert observed_training_ids[0] == [1, 2, 3, 4, 5]
    assert 6 not in observed_training_ids[0]

    # Prediction for draw 10 may use only draws 1-9.
    assert observed_training_ids[-1] == list(range(1, 10))
    assert 10 not in observed_training_ids[-1]
