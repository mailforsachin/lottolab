#!/usr/bin/env python3
"""Ticket portfolio diversity utilities for LottoLab."""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence


class TicketDiversityAnalyzer:
    """Measure overlap and coverage across generated tickets."""

    @staticmethod
    def overlap(a: Sequence[int], b: Sequence[int]) -> int:
        """Return count of shared numbers between two tickets."""
        return len(set(a).intersection(b))

    def analyze(self, tickets: Iterable[Sequence[int]]) -> dict:
        """Return portfolio-level diversity metrics."""
        normalized = [tuple(sorted(map(int, t))) for t in tickets]

        if not normalized:
            raise ValueError("At least one ticket is required.")

        if len(set(normalized)) != len(normalized):
            raise ValueError("Duplicate tickets detected.")

        usage = Counter(
            number
            for ticket in normalized
            for number in ticket
        )

        overlaps = []

        for i in range(len(normalized)):
            for j in range(i + 1, len(normalized)):
                overlaps.append(
                    self.overlap(normalized[i], normalized[j])
                )

        characteristics = []

        for ticket in normalized:
            odd = sum(n % 2 for n in ticket)
            even = len(ticket) - odd

            characteristics.append(
                {
                    "ticket": ticket,
                    "sum": sum(ticket),
                    "odd": odd,
                    "even": even,
                    "consecutive_pairs": sum(
                        1
                        for a, b in zip(ticket, ticket[1:])
                        if b == a + 1
                    ),
                }
            )

        return {
            "ticket_count": len(normalized),
            "unique_numbers_used": len(usage),
            "number_usage": dict(sorted(usage.items())),
            "average_pairwise_overlap": (
                sum(overlaps) / len(overlaps)
                if overlaps else 0.0
            ),
            "maximum_pairwise_overlap": max(overlaps, default=0),
            "characteristics": characteristics,
        }
