#!/usr/bin/env python3
"""Statistical analysis of LottoLab walk-forward strategy results."""

from __future__ import annotations

import argparse
import csv
import random
import statistics
from collections import defaultdict
from pathlib import Path


BASELINE_STRATEGY_ID = 1
BASELINE_NAME = "Random"


def load_results(path: Path) -> list[dict]:
    """Load walk-forward CSV results."""
    if not path.exists():
        raise FileNotFoundError(
            f"Results file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def metric_value(row: dict) -> float:
    """Return average main-number matches per ticket."""
    tickets = int(row["ticket_count"])

    if tickets <= 0:
        raise ValueError(
            "ticket_count must be positive."
        )

    return (
        float(row["total_main_matches"])
        / tickets
    )


def build_paired_results(
    rows: list[dict],
) -> dict:
    """Pair each strategy with Random on identical target draws."""
    grouped = defaultdict(dict)

    for row in rows:
        key = (
            row["game"],
            int(row["target_draw_id"]),
        )

        strategy_id = int(
            row["strategy_id"]
        )

        grouped[key][strategy_id] = row

    comparisons = defaultdict(list)

    for (game, target_id), strategies in grouped.items():
        baseline = strategies.get(
            BASELINE_STRATEGY_ID
        )

        if baseline is None:
            continue

        baseline_value = metric_value(
            baseline
        )

        for strategy_id, row in strategies.items():
            if strategy_id == BASELINE_STRATEGY_ID:
                continue

            difference = (
                metric_value(row)
                - baseline_value
            )

            comparisons[
                (
                    game,
                    strategy_id,
                    row["strategy_name"],
                )
            ].append(difference)

    return comparisons


def bootstrap_mean_ci(
    values: list[float],
    iterations: int = 20_000,
    seed: int = 20260718,
) -> tuple[float, float, float, float]:
    """Bootstrap paired mean difference and 95% CI.

    Returns:
        mean_difference,
        lower_ci,
        upper_ci,
        probability_difference_gt_zero
    """
    if not values:
        raise ValueError(
            "Cannot bootstrap empty values."
        )

    rng = random.Random(seed)

    observed_mean = statistics.mean(
        values
    )

    bootstrap_means = []

    n = len(values)

    for _ in range(iterations):
        sample = [
            values[
                rng.randrange(n)
            ]
            for _ in range(n)
        ]

        bootstrap_means.append(
            statistics.mean(sample)
        )

    bootstrap_means.sort()

    lower_index = int(
        0.025 * iterations
    )

    upper_index = min(
        iterations - 1,
        int(0.975 * iterations),
    )

    lower = bootstrap_means[
        lower_index
    ]

    upper = bootstrap_means[
        upper_index
    ]

    probability_positive = (
        sum(
            value > 0
            for value in bootstrap_means
        )
        / iterations
    )

    return (
        observed_mean,
        lower,
        upper,
        probability_positive,
    )


def classify(
    lower: float,
    upper: float,
) -> str:
    """Give conservative interpretation of confidence interval."""
    if lower > 0:
        return "BETTER THAN RANDOM"

    if upper < 0:
        return "WORSE THAN RANDOM"

    return "NO CLEAR DIFFERENCE"


def main() -> None:
    """Analyze walk-forward results."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        default=(
            "reports/"
            "walkforward_strategy_comparison.csv"
        ),
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=20_000,
    )

    args = parser.parse_args()

    rows = load_results(
        Path(args.input)
    )

    comparisons = build_paired_results(
        rows
    )

    print()
    print("=" * 105)
    print(
        "PAIRED BOOTSTRAP COMPARISON "
        "VS RANDOM"
    )
    print("=" * 105)

    print(
        f"{'Game':<15}"
        f"{'Strategy':<18}"
        f"{'N':>7}"
        f"{'Mean Diff':>13}"
        f"{'95% CI':>25}"
        f"{'P(diff>0)':>13}"
        f"{'Interpretation':>25}"
    )

    print("-" * 105)

    for (
        game,
        strategy_id,
        strategy_name,
    ), differences in sorted(
        comparisons.items()
    ):
        (
            mean_difference,
            lower,
            upper,
            probability_positive,
        ) = bootstrap_mean_ci(
            differences,
            iterations=args.iterations,
            seed=(
                20260718
                + strategy_id
            ),
        )

        interpretation = classify(
            lower,
            upper,
        )

        ci_text = (
            f"[{lower:.5f}, "
            f"{upper:.5f}]"
        )

        print(
            f"{game:<15}"
            f"{strategy_name:<18}"
            f"{len(differences):>7}"
            f"{mean_difference:>13.5f}"
            f"{ci_text:>25}"
            f"{probability_positive:>13.3f}"
            f"{interpretation:>25}"
        )


if __name__ == "__main__":
    main()
