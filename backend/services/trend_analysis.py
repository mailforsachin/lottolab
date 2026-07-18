#!/usr/bin/env python3
"""Rolling frequency, gap, hot/cold, pair and triplet analytics."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Iterable, Sequence


class TrendAnalyzer:
    """Calculate descriptive statistics without modifying historical data."""

    def __init__(self, max_number: int) -> None:
        if max_number < 1:
            raise ValueError("max_number must be positive.")
        self.max_number = max_number

    def analyze(
        self,
        draws: Iterable[Sequence[int]],
        window: int = 100,
    ) -> dict:
        """Return rolling descriptive statistics for a draw window."""
        draw_list = [tuple(map(int, draw)) for draw in draws]

        if not draw_list:
            raise ValueError("No draws supplied.")

        if window < 1:
            raise ValueError("window must be positive.")

        recent = draw_list[-window:]

        frequency = Counter(
            number
            for draw in recent
            for number in draw
        )

        pair_frequency = Counter(
            pair
            for draw in recent
            for pair in combinations(sorted(draw), 2)
        )

        triplet_frequency = Counter(
            triplet
            for draw in recent
            for triplet in combinations(sorted(draw), 3)
        )

        gaps = {}

        for number in range(1, self.max_number + 1):
            gap = len(draw_list)

            for age, draw in enumerate(reversed(draw_list)):
                if number in draw:
                    gap = age
                    break

            gaps[number] = gap

        ranked_hot = sorted(
            range(1, self.max_number + 1),
            key=lambda n: (-frequency[n], n),
        )

        ranked_cold = sorted(
            range(1, self.max_number + 1),
            key=lambda n: (frequency[n], n),
        )

        return {
            "window": min(window, len(draw_list)),
            "frequencies": dict(frequency),
            "gaps_since_last_seen": gaps,
            "hot_numbers": ranked_hot[:10],
            "cold_numbers": ranked_cold[:10],
            "top_pairs": pair_frequency.most_common(20),
            "top_triplets": triplet_frequency.most_common(20),
        }
