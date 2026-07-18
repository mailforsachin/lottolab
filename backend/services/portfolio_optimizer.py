"""
Deterministic structural portfolio optimizer for lottery tickets.

This module implements a greedy forward selection algorithm that optimizes
the structural diversity of a ticket portfolio using PortfolioScorer.
"""

from dataclasses import dataclass, field
from typing import List, Set, Tuple, Optional, FrozenSet, Sequence
import copy

from backend.services.portfolio_scorer import PortfolioScorer, PortfolioScore


@dataclass(frozen=True)
class PortfolioOptimizerResult:
    """Immutable result of portfolio optimization."""
    selected_tickets: Tuple[Tuple[int, ...], ...] = field(default_factory=tuple)
    candidate_count: int = 0
    portfolio_size: int = 0
    portfolio_score: Optional[PortfolioScore] = None
    seed: int = 0
    algorithm: str = "greedy_forward_selection"
    converged: bool = False


class PortfolioOptimizer:
    """
    Deterministic greedy forward selection optimizer for lottery portfolios.

    Selects exactly portfolio_size tickets from candidates that maximize
    structural diversity as measured by PortfolioScorer.
    """

    def __init__(self, max_number: int = 49, numbers_per_ticket: int = 6):
        """
        Initialize the portfolio optimizer.

        Args:
            max_number: Maximum number allowed in a ticket (default 49)
            numbers_per_ticket: Number of numbers per ticket (default 6)
        """
        if max_number < 1:
            raise ValueError("max_number must be >= 1")
        if numbers_per_ticket < 1:
            raise ValueError("numbers_per_ticket must be >= 1")
        if numbers_per_ticket > max_number:
            raise ValueError("numbers_per_ticket cannot exceed max_number")

        self.max_number = max_number
        self.numbers_per_ticket = numbers_per_ticket
        self.scorer = PortfolioScorer(
            max_number=max_number,
            numbers_per_ticket=numbers_per_ticket
        )

    def _normalize_ticket(self, ticket: List[int]) -> Tuple[int, ...]:
        """
        Normalize a ticket to a sorted immutable tuple.

        Validates:
        - Must be a list
        - Must contain exactly numbers_per_ticket values
        - All values must be int (not bool)
        - All values must be between 1 and max_number
        - All values must be unique

        Args:
            ticket: List of numbers

        Returns:
            Sorted tuple of numbers

        Raises:
            ValueError: If ticket is malformed
        """
        # Validate container type
        if not isinstance(ticket, list):
            raise ValueError(f"Invalid ticket: {ticket}")

        # Check length
        if len(ticket) != self.numbers_per_ticket:
            raise ValueError(f"Invalid ticket: {ticket}")

        # Validate each element is int (not bool) and in range
        for num in ticket:
            if not isinstance(num, int) or isinstance(num, bool):
                raise ValueError(f"Invalid ticket: {ticket}")
            if num < 1 or num > self.max_number:
                raise ValueError(f"Invalid ticket: {ticket}")

        # Check uniqueness
        if len(set(ticket)) != self.numbers_per_ticket:
            raise ValueError(f"Invalid ticket: {ticket}")

        # Return sorted tuple
        return tuple(sorted(ticket))

    def _validate_all_candidates(self, candidates: List[List[int]]) -> Tuple[Tuple[int, ...], ...]:
        """
        Validate all candidates and return normalized tickets.

        Args:
            candidates: List of ticket candidates

        Returns:
            Tuple of normalized valid tickets

        Raises:
            ValueError: If any candidate is malformed
        """
        normalized = []
        for ticket in candidates:
            normalized.append(self._normalize_ticket(ticket))
        return tuple(normalized)

    def _deduplicate_candidates(
        self,
        candidates: Tuple[Tuple[int, ...], ...]
    ) -> List[Tuple[int, ...]]:
        """
        Deduplicate normalized tickets while preserving order.

        Args:
            candidates: Tuple of normalized tickets

        Returns:
            List of unique tickets in original order
        """
        seen: Set[Tuple[int, ...]] = set()
        unique = []
        for ticket in candidates:
            if ticket not in seen:
                seen.add(ticket)
                unique.append(ticket)
        return unique

    def optimize(
        self,
        candidates: List[List[int]],
        portfolio_size: int = 33,
        seed: int = 0
    ) -> PortfolioOptimizerResult:
        """
        Select exactly portfolio_size tickets using greedy forward selection.

        Args:
            candidates: List of ticket candidates (lists of numbers)
            portfolio_size: Number of tickets to select (default 33)
            seed: Deterministic seed for reproducibility (default 0)

        Returns:
            PortfolioOptimizerResult with selected tickets and score

        Raises:
            ValueError: If portfolio_size < 1 or insufficient valid candidates
        """
        if portfolio_size < 1:
            raise ValueError(f"portfolio_size must be >= 1, got {portfolio_size}")

        # Validate and normalize all candidates
        validated = self._validate_all_candidates(candidates)

        if not validated:
            raise ValueError("No valid candidates provided")

        unique_candidates = self._deduplicate_candidates(validated)

        if len(unique_candidates) < portfolio_size:
            raise ValueError(
                f"Insufficient unique valid candidates: {len(unique_candidates)} "
                f"available, {portfolio_size} required"
            )

        # Greedy forward selection
        selected: List[Tuple[int, ...]] = []
        remaining = unique_candidates.copy()

        for _ in range(portfolio_size):
            best_score = None
            best_ticket = None
            best_idx = -1

            for idx, ticket in enumerate(remaining):
                # Build proposed portfolio
                proposed = selected + [ticket]
                score = self.scorer.score(proposed)

                if best_score is None or score.score > best_score.score:
                    best_score = score
                    best_ticket = ticket
                    best_idx = idx

            if best_ticket is None:
                raise RuntimeError("Failed to select a ticket during optimization")

            selected.append(best_ticket)
            remaining.pop(best_idx)

        # Calculate final score
        final_score = self.scorer.score(selected)

        return PortfolioOptimizerResult(
            selected_tickets=tuple(selected),
            candidate_count=len(unique_candidates),
            portfolio_size=portfolio_size,
            portfolio_score=final_score,
            seed=seed,
            algorithm="greedy_forward_selection",
            converged=True
        )

    def optimize_lotto649(self, candidates: List[List[int]], portfolio_size: int = 33) -> PortfolioOptimizerResult:
        """Convenience method for Lotto 6/49 (6 numbers, 1-49)."""
        return self.optimize(candidates, portfolio_size)

    def optimize_dailygrand(self, candidates: List[List[int]], portfolio_size: int = 33) -> PortfolioOptimizerResult:
        """Convenience method for Daily Grand (5 numbers, 1-49)."""
        return self.optimize(candidates, portfolio_size)


def optimize_portfolio(
    candidates: List[List[int]],
    portfolio_size: int = 33,
    max_number: int = 49,
    numbers_per_ticket: int = 6,
    seed: int = 0
) -> PortfolioOptimizerResult:
    """
    Convenience function to optimize a ticket portfolio.

    Args:
        candidates: List of ticket candidates
        portfolio_size: Number of tickets to select
        max_number: Maximum number allowed (default 49)
        numbers_per_ticket: Numbers per ticket (default 6)
        seed: Deterministic seed

    Returns:
        PortfolioOptimizerResult
    """
    optimizer = PortfolioOptimizer(
        max_number=max_number,
        numbers_per_ticket=numbers_per_ticket
    )
    return optimizer.optimize(candidates, portfolio_size, seed)
