#!/usr/bin/env python3
"""Generate weekly LottoLab tickets using database-derived frequencies.

Legacy generator retained for operational compatibility.

Important:
    This generator performs descriptive hot/cold sampling. It is not the
    validated walk-forward strategy engine and should not be described as
    predictive.
"""

from __future__ import annotations

import random
from collections import Counter
from datetime import datetime

from backend.database.base import SyncSessionLocal
from backend.models import Draw


def get_hot_numbers_from_db(
    game_type: str,
    limit: int = 10,
) -> list[int]:
    """Return the most frequently observed main numbers for a game."""
    session = SyncSessionLocal()

    try:
        rows = (
            session.query(Draw)
            .filter(Draw.lottery_type == game_type)
            .all()
        )

        if not rows:
            print(f"No draws found for {game_type}.")
            return []

        frequency: Counter[int] = Counter()

        for row in rows:
            numbers = [int(value) for value in row.numbers]

            # Daily Grand stores the Grand Number as the sixth value.
            if game_type == "Daily Grand":
                numbers = numbers[:5]

            frequency.update(numbers)

        hot_numbers = [
            number
            for number, _count
            in frequency.most_common(limit)
        ]

        print(
            f"Found {len(rows)} draws for {game_type}."
        )
        print(
            f"Most frequent main numbers: {hot_numbers[:5]}"
        )

        return hot_numbers

    except Exception as exc:
        print(
            f"Unable to calculate frequencies for "
            f"{game_type}: {exc}"
        )
        return []

    finally:
        session.close()


def generate_dailygrand_tickets(
    hot_numbers: list[int],
    num_tickets: int = 33,
    seed: int | None = None,
) -> list[tuple[list[int], int]]:
    """Generate unique Daily Grand tickets.

    The Grand Number is sampled uniformly from 1 through 7.
    """
    rng = random.Random(seed)

    if len(hot_numbers) < 8:
        hot_numbers = list(range(1, 50))

    cold_numbers = [
        number
        for number in range(1, 50)
        if number not in hot_numbers[:10]
    ]

    tickets: list[tuple[list[int], int]] = []
    seen: set[tuple[tuple[int, ...], int]] = set()

    attempts = 0

    while len(tickets) < num_tickets:
        attempts += 1

        if attempts > 20_000:
            raise RuntimeError(
                "Unable to generate enough unique Daily Grand tickets."
            )

        if len(tickets) < num_tickets // 2:
            numbers = sorted(
                rng.sample(
                    hot_numbers[:max(8, min(10, len(hot_numbers)))],
                    5,
                )
            )
        else:
            hot = rng.sample(
                hot_numbers[:min(10, len(hot_numbers))],
                3,
            )

            available_cold = [
                number
                for number in cold_numbers
                if number not in hot
            ]

            cold = rng.sample(
                available_cold,
                2,
            )

            numbers = sorted(hot + cold)

        grand = rng.randint(1, 7)

        key = (
            tuple(numbers),
            grand,
        )

        if key in seen:
            continue

        seen.add(key)
        tickets.append(
            (numbers, grand)
        )

    return tickets


def generate_lotto649_tickets(
    hot_numbers: list[int],
    num_tickets: int = 33,
    seed: int | None = None,
) -> list[list[int]]:
    """Generate unique Lotto 6/49 tickets."""
    rng = random.Random(seed)

    if len(hot_numbers) < 8:
        hot_numbers = list(range(1, 50))

    cold_numbers = [
        number
        for number in range(1, 50)
        if number not in hot_numbers[:10]
    ]

    tickets: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()

    attempts = 0

    while len(tickets) < num_tickets:
        attempts += 1

        if attempts > 20_000:
            raise RuntimeError(
                "Unable to generate enough unique Lotto 6/49 tickets."
            )

        # There are only C(8,6)=28 all-hot combinations, so avoid
        # concentrating half the portfolio inside that tiny space.
        if len(tickets) < num_tickets // 3:
            numbers = sorted(
                rng.sample(
                    hot_numbers[:min(10, len(hot_numbers))],
                    6,
                )
            )
        else:
            hot = rng.sample(
                hot_numbers[:min(10, len(hot_numbers))],
                3,
            )

            available_cold = [
                number
                for number in cold_numbers
                if number not in hot
            ]

            cold = rng.sample(
                available_cold,
                3,
            )

            numbers = sorted(hot + cold)

        key = tuple(numbers)

        if key in seen:
            continue

        seen.add(key)
        tickets.append(numbers)

    return tickets


def main() -> None:
    """Generate and display weekly ticket portfolios."""
    print("=" * 60)
    print(
        "WEEKLY TICKETS - "
        f"{datetime.now().strftime('%Y-%m-%d')}"
    )
    print("=" * 60)

    print("\nDAILY GRAND")
    print("-" * 40)

    daily_hot = get_hot_numbers_from_db(
        "Daily Grand"
    )

    daily_tickets = generate_dailygrand_tickets(
        daily_hot,
        33,
    )

    for index, (numbers, grand) in enumerate(
        daily_tickets,
        start=1,
    ):
        print(
            f"{index:2}. {numbers} | Grand: {grand}"
        )

    print("\nLOTTO 6/49")
    print("-" * 40)

    lotto_hot = get_hot_numbers_from_db(
        "6/49"
    )

    lotto_tickets = generate_lotto649_tickets(
        lotto_hot,
        33,
    )

    for index, numbers in enumerate(
        lotto_tickets,
        start=1,
    ):
        print(
            f"{index:2}. {numbers}"
        )


if __name__ == "__main__":
    main()
