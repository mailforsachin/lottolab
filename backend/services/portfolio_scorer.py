#!/usr/bin/env python3
"""Portfolio-level scoring and diversity analysis for LottoLab.

This module evaluates structural diversity across a collection of lottery
tickets. It does not predict future lottery outcomes and does not modify
historical data.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from statistics import mean
from typing import Iterable, Sequence


Ticket = tuple[int, ...]


@dataclass(frozen=True)
class PortfolioScore:
    """Immutable structural-diversity metrics for one ticket portfolio."""

    ticket_count: int
    unique_numbers_used: int
    coverage_ratio: float
    average_pairwise_overlap: float
    maximum_pairwise_overlap: int
    repeated_pair_count: int
    repeated_triplet_count: int
    number_usage_stddev: float
    odd_even_patterns: int
    sum_range: int
    score: float


class PortfolioScorer:
    """Measure structural diversity of a fixed lottery-ticket portfolio."""

    def __init__(
        self,
        max_number: int = 49,
        numbers_per_ticket: int = 6,
    ) -> None:
        if max_number < 1:
            raise ValueError("max_number must be positive.")

        if numbers_per_ticket < 1:
            raise ValueError(
                "numbers_per_ticket must be positive."
            )

        if numbers_per_ticket > max_number:
            raise ValueError(
                "numbers_per_ticket cannot exceed max_number."
            )

        self.max_number = max_number
        self.numbers_per_ticket = numbers_per_ticket

    def _normalize_ticket(
        self,
        ticket: Sequence[int],
    ) -> Ticket:
        """Validate and normalize one ticket."""
        try:
            normalized = tuple(
                sorted(int(number) for number in ticket)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Ticket contains a non-integer value."
            ) from exc

        if len(normalized) != self.numbers_per_ticket:
            raise ValueError(
                f"Ticket contains {len(normalized)} numbers; "
                f"expected {self.numbers_per_ticket}."
            )

        if len(set(normalized)) != len(normalized):
            raise ValueError(
                f"Ticket contains duplicate numbers: {normalized}"
            )

        if any(
            number < 1 or number > self.max_number
            for number in normalized
        ):
            raise ValueError(
                f"Ticket contains a number outside "
                f"1..{self.max_number}."
            )

        return normalized

    @staticmethod
    def _population_stddev(
        values: Sequence[int],
    ) -> float:
        """Return population standard deviation without external libraries."""
        if not values:
            return 0.0

        average = mean(values)

        variance = mean(
            (value - average) ** 2
            for value in values
        )

        return variance ** 0.5

    def score(
        self,
        tickets: Iterable[Sequence[int]],
    ) -> PortfolioScore:
        """Return structural-diversity metrics for a portfolio."""
        normalized = tuple(
            self._normalize_ticket(ticket)
            for ticket in tickets
        )

        if not normalized:
            raise ValueError(
                "At least one ticket is required."
            )

        if len(set(normalized)) != len(normalized):
            raise ValueError(
                "Duplicate tickets are not allowed."
            )

        number_usage = Counter(
            number
            for ticket in normalized
            for number in ticket
        )

        unique_numbers = len(number_usage)

        coverage_ratio = (
            unique_numbers / self.max_number
        )

        overlaps = [
            len(set(left).intersection(right))
            for left, right in combinations(
                normalized,
                2,
            )
        ]

        average_overlap = (
            mean(overlaps)
            if overlaps
            else 0.0
        )

        maximum_overlap = (
            max(overlaps)
            if overlaps
            else 0
        )

        pair_usage = Counter(
            pair
            for ticket in normalized
            for pair in combinations(ticket, 2)
        )

        triplet_usage = Counter(
            triplet
            for ticket in normalized
            for triplet in combinations(ticket, 3)
        )

        repeated_pair_count = sum(
            count - 1
            for count in pair_usage.values()
            if count > 1
        )

        repeated_triplet_count = sum(
            count - 1
            for count in triplet_usage.values()
            if count > 1
        )

        usage_vector = [
            number_usage.get(number, 0)
            for number in range(
                1,
                self.max_number + 1,
            )
        ]

        usage_stddev = self._population_stddev(
            usage_vector
        )

        parity_patterns = {
            sum(
                number % 2
                for number in ticket
            )
            for ticket in normalized
        }

        sums = [
            sum(ticket)
            for ticket in normalized
        ]

        sum_range = (
            max(sums) - min(sums)
            if len(sums) > 1
            else 0
        )

        # Structural score only.
        #
        # Higher coverage and parity diversity are rewarded.
        # Excessive overlap, repeated pairs/triplets, and uneven number
        # concentration are penalized.
        #
        # This score is intentionally not a probability of winning.
        overlap_penalty = (
            average_overlap
            / self.numbers_per_ticket
        )

        pair_denominator = max(
            1,
            len(normalized)
            * (
                self.numbers_per_ticket
                * (self.numbers_per_ticket - 1)
                // 2
            ),
        )

        triplet_denominator = max(
            1,
            len(normalized)
            * (
                self.numbers_per_ticket
                * (self.numbers_per_ticket - 1)
                * (self.numbers_per_ticket - 2)
                // 6
            ),
        )

        pair_penalty = (
            repeated_pair_count
            / pair_denominator
        )

        triplet_penalty = (
            repeated_triplet_count
            / triplet_denominator
        )

        usage_penalty = (
            usage_stddev
            / max(1.0, len(normalized))
        )

        parity_diversity = (
            len(parity_patterns)
            / (self.numbers_per_ticket + 1)
        )

        raw_score = (
            0.40 * coverage_ratio
            + 0.15 * parity_diversity
            - 0.20 * overlap_penalty
            - 0.10 * pair_penalty
            - 0.10 * triplet_penalty
            - 0.05 * usage_penalty
        )

        score = max(
            0.0,
            min(100.0, raw_score * 100.0),
        )

        return PortfolioScore(
            ticket_count=len(normalized),
            unique_numbers_used=unique_numbers,
            coverage_ratio=coverage_ratio,
            average_pairwise_overlap=average_overlap,
            maximum_pairwise_overlap=maximum_overlap,
            repeated_pair_count=repeated_pair_count,
            repeated_triplet_count=repeated_triplet_count,
            number_usage_stddev=usage_stddev,
            odd_even_patterns=len(parity_patterns),
            sum_range=sum_range,
            score=score,
        )
