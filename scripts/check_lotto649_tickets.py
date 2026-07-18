#!/usr/bin/env python3
"""Display Lotto 6/49 frequency statistics and sample tickets.

This utility reads historical draw data through LottoLab's shared
SQLAlchemy configuration. It does not modify historical data.

The generated examples are descriptive samples only and should not
be interpreted as predictions.
"""

from __future__ import annotations

import random
from collections import Counter

from backend.database.base import SyncSessionLocal
from backend.models import Draw


def get_hot_numbers(limit: int = 10) -> list[int]:
    """Return the most frequently observed Lotto 6/49 main numbers."""
    if limit < 6:
        raise ValueError("limit must be at least 6.")

    session = SyncSessionLocal()

    try:
        rows = (
            session.query(Draw)
            .filter(Draw.lottery_type == "6/49")
            .all()
        )

        if not rows:
            raise RuntimeError(
                "No Lotto 6/49 historical draws were found."
            )

        frequency: Counter[int] = Counter()

        for row in rows:
            numbers = [
                int(number)
                for number in row.numbers
            ]

            if len(numbers) != 6:
                raise ValueError(
                    f"Draw {row.id} contains "
                    f"{len(numbers)} main numbers; expected 6."
                )

            frequency.update(numbers)

        return [
            number
            for number, _count
            in frequency.most_common(limit)
        ]

    finally:
        session.close()


def generate_sample_tickets(
    hot_numbers: list[int],
    ticket_count: int = 5,
    seed: int | None = None,
) -> list[list[int]]:
    """Generate unique descriptive sample tickets."""
    if ticket_count < 1:
        raise ValueError(
            "ticket_count must be positive."
        )

    if len(hot_numbers) < 10:
        raise ValueError(
            "At least 10 ranked numbers are required."
        )

    rng = random.Random(seed)

    cold_numbers = [
        number
        for number in range(1, 50)
        if number not in hot_numbers[:10]
    ]

    tickets: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()

    attempts = 0

    while len(tickets) < ticket_count:
        attempts += 1

        if attempts > 10_000:
            raise RuntimeError(
                "Unable to generate enough unique sample tickets."
            )

        if len(tickets) < 2:
            ticket = sorted(
                rng.sample(
                    hot_numbers[:10],
                    6,
                )
            )
        else:
            hot = rng.sample(
                hot_numbers[:10],
                3,
            )

            cold = rng.sample(
                cold_numbers,
                3,
            )

            ticket = sorted(hot + cold)

        key = tuple(ticket)

        if key in seen:
            continue

        seen.add(key)
        tickets.append(ticket)

    return tickets


def main() -> None:
    """Print frequency information and sample tickets."""
    try:
        hot_numbers = get_hot_numbers()

        print(
            "Lotto 6/49 most frequent numbers:",
            hot_numbers[:6],
        )

        print(
            "\nSample Lotto 6/49 tickets "
            "(descriptive, not predictive):"
        )

        tickets = generate_sample_tickets(
            hot_numbers,
            ticket_count=5,
        )

        for index, ticket in enumerate(
            tickets,
            start=1,
        ):
            print(
                f"Ticket {index}: {ticket}"
            )

    except Exception as exc:
        print(
            f"Unable to generate sample tickets: {exc}"
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
