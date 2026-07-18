#!/usr/bin/env python3
"""Leakage-safe walk-forward comparison of LottoLab strategies.

This script is READ ONLY with respect to the LottoLab database.

It compares all registered ticket-generation strategies using identical
out-of-sample target draws. Each generated portfolio is evaluated against
exactly one subsequent historical draw.

No historical draw, simulation, or ticket records are modified.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from sqlalchemy.orm import sessionmaker

from backend.core.algorithms.base import (
    DAILY_GRAND,
    LOTTO_649,
    GameConfig,
    GeneratedTicket,
)
from backend.core.algorithms.registry import get_strategy
from backend.database.base import sync_engine
from backend.models import Draw
from backend.services.walk_forward_backtest import HistoricalDraw


STRATEGY_NAMES = {
    1: "Random",
    2: "Sobol",
    3: "Monte Carlo",
    4: "Genetic",
    5: "Hybrid",
}


@dataclass
class TargetResult:
    """Aggregated result for one strategy on one unseen target draw."""

    game: str
    strategy_id: int
    strategy_name: str
    target_draw_id: int
    target_date: str
    training_size: int
    ticket_count: int
    total_main_matches: int
    best_main_match: int
    tickets_with_2_plus: int
    tickets_with_3_plus: int
    tickets_with_4_plus: int
    tickets_with_5_plus: int
    tickets_with_6: int
    grand_matches: int
    exact_top_tier_matches: int
    runtime_seconds: float


def load_draws(game_name: str) -> list[HistoricalDraw]:
    """Load one game's historical draws chronologically.

    This function performs SELECT queries only.
    """
    Session = sessionmaker(bind=sync_engine)
    session = Session()

    try:
        rows = (
            session.query(Draw)
            .filter(Draw.lottery_type == game_name)
            .order_by(Draw.draw_date.asc(), Draw.id.asc())
            .all()
        )

        historical: list[HistoricalDraw] = []

        for row in rows:
            raw = tuple(int(value) for value in row.numbers)

            if game_name == "Daily Grand":
                if len(raw) < 6:
                    raise ValueError(
                        f"Daily Grand draw {row.id} has "
                        f"{len(raw)} values; expected at least 6."
                    )

                main_numbers = tuple(sorted(raw[:5]))
                grand_number = int(raw[5])

                # Data-quality guard: current database appears to duplicate
                # the Grand Number in the bonus column.
                if (
                    row.bonus is not None
                    and int(row.bonus) != grand_number
                ):
                    raise ValueError(
                        f"Daily Grand draw {row.id}: numbers[5]="
                        f"{grand_number} but bonus={row.bonus}."
                    )

            else:
                if len(raw) != 6:
                    raise ValueError(
                        f"6/49 draw {row.id} has "
                        f"{len(raw)} main numbers; expected 6."
                    )

                main_numbers = tuple(sorted(raw))
                grand_number = None

            historical.append(
                HistoricalDraw(
                    draw_id=row.id,
                    numbers=main_numbers,
                    grand_number=grand_number,
                )
            )

        return historical

    finally:
        session.close()


def score_portfolio(
    tickets: Sequence[GeneratedTicket],
    target: HistoricalDraw,
    game: GameConfig,
) -> dict:
    """Score a frozen portfolio against exactly one target draw."""
    main_match_counts: list[int] = []
    grand_matches = 0
    exact_top_tier_matches = 0

    target_main = set(target.numbers)

    for ticket in tickets:
        matches = len(
            set(ticket.numbers).intersection(target_main)
        )

        main_match_counts.append(matches)

        grand_match = (
            game.grand_max is not None
            and ticket.grand_number == target.grand_number
        )

        if grand_match:
            grand_matches += 1

        if game.grand_max is None:
            if matches == game.main_numbers_drawn:
                exact_top_tier_matches += 1
        else:
            if (
                matches == game.main_numbers_drawn
                and grand_match
            ):
                exact_top_tier_matches += 1

    return {
        "total_main_matches": sum(main_match_counts),
        "best_main_match": max(main_match_counts, default=0),
        "tickets_with_2_plus": sum(
            value >= 2 for value in main_match_counts
        ),
        "tickets_with_3_plus": sum(
            value >= 3 for value in main_match_counts
        ),
        "tickets_with_4_plus": sum(
            value >= 4 for value in main_match_counts
        ),
        "tickets_with_5_plus": sum(
            value >= 5 for value in main_match_counts
        ),
        "tickets_with_6": sum(
            value >= 6 for value in main_match_counts
        ),
        "grand_matches": grand_matches,
        "exact_top_tier_matches": exact_top_tier_matches,
    }


def mean_confidence_interval(
    values: Sequence[float],
) -> tuple[float, float, float]:
    """Return mean and approximate 95% confidence interval."""
    if not values:
        return 0.0, 0.0, 0.0

    avg = statistics.mean(values)

    if len(values) < 2:
        return avg, avg, avg

    standard_error = (
        statistics.stdev(values)
        / math.sqrt(len(values))
    )

    margin = 1.96 * standard_error

    return avg, avg - margin, avg + margin


def run_game(
    game: GameConfig,
    target_count: int,
    ticket_count: int,
    minimum_training: int,
    seed: int,
) -> list[TargetResult]:
    """Run all strategies on identical unseen target draws."""
    draws = load_draws(game.name)

    if len(draws) <= minimum_training:
        raise ValueError(
            f"{game.name}: only {len(draws)} draws available; "
            f"minimum training is {minimum_training}."
        )

    first_target_index = max(
        minimum_training,
        len(draws) - target_count,
    )

    targets = list(
        range(first_target_index, len(draws))
    )

    print()
    print("=" * 78)
    print(
        f"{game.name}: {len(draws)} historical draws | "
        f"{len(targets)} unseen targets | "
        f"{ticket_count} tickets/strategy/target"
    )
    print("=" * 78)

    results: list[TargetResult] = []

    for strategy_id in range(1, 6):
        strategy = get_strategy(strategy_id)

        print(
            f"\n[{strategy_id}/5] "
            f"{STRATEGY_NAMES[strategy_id]}"
        )

        strategy_start = time.perf_counter()

        for position, target_index in enumerate(
            targets,
            start=1,
        ):
            training = tuple(draws[:target_index])
            target = draws[target_index]

            # Same target receives a deterministic seed for each strategy.
            # Different strategies get different seed namespaces.
            run_seed = (
                seed
                + target.draw_id
                + (strategy_id * 1_000_000)
            )

            start = time.perf_counter()

            tickets = strategy.generate(
                training_draws=training,
                ticket_count=ticket_count,
                game=game,
                seed=run_seed,
            )

            runtime = time.perf_counter() - start

            scores = score_portfolio(
                tickets=tickets,
                target=target,
                game=game,
            )

            results.append(
                TargetResult(
                    game=game.name,
                    strategy_id=strategy_id,
                    strategy_name=STRATEGY_NAMES[
                        strategy_id
                    ],
                    target_draw_id=target.draw_id,
                    target_date="historical",
                    training_size=len(training),
                    ticket_count=ticket_count,
                    runtime_seconds=runtime,
                    **scores,
                )
            )

            if (
                position % 10 == 0
                or position == len(targets)
            ):
                print(
                    f"  completed "
                    f"{position}/{len(targets)} targets",
                    flush=True,
                )

        elapsed = time.perf_counter() - strategy_start

        print(
            f"  runtime: {elapsed:.2f}s"
        )

    return results


def print_summary(
    results: Sequence[TargetResult],
) -> None:
    """Print strategy comparison summary."""
    print()
    print("=" * 110)
    print("WALK-FORWARD RESULTS")
    print("=" * 110)

    games = sorted(
        {result.game for result in results}
    )

    for game in games:
        print(f"\n{game}")
        print("-" * 110)

        header = (
            f"{'Strategy':<15}"
            f"{'Targets':>9}"
            f"{'AvgMatch':>11}"
            f"{'95% CI':>23}"
            f"{'3+':>9}"
            f"{'4+':>9}"
            f"{'5+':>9}"
            f"{'Best':>8}"
            f"{'Grand':>9}"
        )

        print(header)

        for strategy_id in range(1, 6):
            rows = [
                result
                for result in results
                if (
                    result.game == game
                    and result.strategy_id == strategy_id
                )
            ]

            if not rows:
                continue

            # Average number of matching main numbers per ticket.
            per_ticket_matches = [
                row.total_main_matches
                / row.ticket_count
                for row in rows
            ]

            avg, low, high = mean_confidence_interval(
                per_ticket_matches
            )

            total_3 = sum(
                row.tickets_with_3_plus
                for row in rows
            )

            total_4 = sum(
                row.tickets_with_4_plus
                for row in rows
            )

            total_5 = sum(
                row.tickets_with_5_plus
                for row in rows
            )

            best = max(
                row.best_main_match
                for row in rows
            )

            grand = sum(
                row.grand_matches
                for row in rows
            )

            print(
                f"{STRATEGY_NAMES[strategy_id]:<15}"
                f"{len(rows):>9}"
                f"{avg:>11.4f}"
                f"{f'[{low:.4f}, {high:.4f}]':>23}"
                f"{total_3:>9}"
                f"{total_4:>9}"
                f"{total_5:>9}"
                f"{best:>8}"
                f"{grand:>9}"
            )


def save_results(
    results: Sequence[TargetResult],
    output_dir: Path,
) -> None:
    """Save detailed CSV and JSON results."""
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = (
        output_dir
        / "walkforward_strategy_comparison.csv"
    )

    json_path = (
        output_dir
        / "walkforward_strategy_comparison.json"
    )

    rows = [
        asdict(result)
        for result in results
    ]

    if rows:
        with csv_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=list(rows[0].keys()),
            )

            writer.writeheader()
            writer.writerows(rows)

    with json_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            rows,
            handle,
            indent=2,
        )

    print()
    print(f"CSV:  {csv_path}")
    print(f"JSON: {json_path}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Leakage-safe LottoLab strategy comparison."
        )
    )

    parser.add_argument(
        "--targets",
        type=int,
        default=100,
        help="Number of latest historical target draws per game.",
    )

    parser.add_argument(
        "--tickets",
        type=int,
        default=33,
        help="Tickets generated per strategy per target draw.",
    )

    parser.add_argument(
        "--minimum-training",
        type=int,
        default=500,
        help="Minimum prior draws required before evaluation.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=20260718,
        help="Base deterministic random seed.",
    )

    parser.add_argument(
        "--game",
        choices=["649", "dailygrand", "both"],
        default="both",
    )

    parser.add_argument(
        "--output-dir",
        default="reports",
    )

    return parser.parse_args()


def main() -> None:
    """Run command-line strategy comparison."""
    args = parse_args()

    if args.targets < 1:
        raise ValueError("--targets must be positive.")

    if args.tickets < 1:
        raise ValueError("--tickets must be positive.")

    all_results: list[TargetResult] = []

    if args.game in ("649", "both"):
        all_results.extend(
            run_game(
                game=LOTTO_649,
                target_count=args.targets,
                ticket_count=args.tickets,
                minimum_training=args.minimum_training,
                seed=args.seed,
            )
        )

    if args.game in ("dailygrand", "both"):
        all_results.extend(
            run_game(
                game=DAILY_GRAND,
                target_count=args.targets,
                ticket_count=args.tickets,
                minimum_training=args.minimum_training,
                seed=args.seed,
            )
        )

    print_summary(all_results)

    save_results(
        all_results,
        Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
