"""
Tests for the deterministic structural portfolio optimizer.
"""

import pytest
import copy
from backend.services.portfolio_optimizer import (
    PortfolioOptimizer,
    PortfolioOptimizerResult,
    optimize_portfolio
)
from backend.services.portfolio_scorer import PortfolioScorer


class TestPortfolioOptimizer:
    """Test suite for PortfolioOptimizer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = PortfolioOptimizer(max_number=49, numbers_per_ticket=6)

    def test_optimize_selects_exact_number(self):
        """Test that optimize selects exactly portfolio_size tickets."""
        candidates = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
            [19, 20, 21, 22, 23, 24],
            [25, 26, 27, 28, 29, 30],
            [31, 32, 33, 34, 35, 36],
            [37, 38, 39, 40, 41, 42],
            [43, 44, 45, 46, 47, 48],
        ]

        result = self.optimizer.optimize(candidates, portfolio_size=5)
        assert len(result.selected_tickets) == 5
        assert result.portfolio_size == 5

    def test_optimize_selects_unique_tickets(self):
        """Test that all selected tickets are unique."""
        candidates = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
            [19, 20, 21, 22, 23, 24],
            [25, 26, 27, 28, 29, 30],
        ]

        result = self.optimizer.optimize(candidates, portfolio_size=5)
        unique_tickets = {tuple(ticket) for ticket in result.selected_tickets}
        assert len(unique_tickets) == 5

    def test_optimize_all_from_candidate_pool(self):
        """Test that all selected tickets originate from the candidate pool."""
        candidates = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
        ]
        candidate_set = {tuple(t) for t in candidates}

        result = self.optimizer.optimize(candidates, portfolio_size=3)
        for ticket in result.selected_tickets:
            assert tuple(ticket) in candidate_set

    def test_optimize_deterministic(self):
        """Test that multiple runs produce the same result."""
        candidates = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
            [19, 20, 21, 22, 23, 24],
            [25, 26, 27, 28, 29, 30],
        ]

        result1 = self.optimizer.optimize(candidates, portfolio_size=3, seed=42)
        result2 = self.optimizer.optimize(candidates, portfolio_size=3, seed=42)

        assert result1.selected_tickets == result2.selected_tickets
        assert result1.portfolio_score == result2.portfolio_score

    def test_insufficient_candidates_raises_error(self):
        """Test that insufficient candidates raises ValueError."""
        candidates = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
        ]

        with pytest.raises(ValueError, match="Insufficient unique valid candidates"):
            self.optimizer.optimize(candidates, portfolio_size=5)

    def test_invalid_portfolio_size_raises_error(self):
        """Test that portfolio_size < 1 raises ValueError."""
        candidates = [[1, 2, 3, 4, 5, 6]]

        with pytest.raises(ValueError, match="portfolio_size must be >= 1"):
            self.optimizer.optimize(candidates, portfolio_size=0)

        with pytest.raises(ValueError, match="portfolio_size must be >= 1"):
            self.optimizer.optimize(candidates, portfolio_size=-1)

    def test_malformed_ticket_rejected(self):
        """Test that malformed tickets are rejected with ValueError."""
        candidates = [
            [1, 2, 3, 4, 5, 6],  # Valid
        ]

        malformed = [
            [1, 2, 3, 4, 5],           # Too few numbers
            [1, 2, 3, 4, 5, 50],       # Number out of range
            [1, 2, 3, 4, 5, 5],        # Duplicate numbers
            "not a list",               # Not a list
            [1, 2, 3, 4, 5, 6, 7],     # Too many numbers
            [1, 2, 3, 4, 5, True],     # bool instead of int
        ]

        for bad in malformed:
            test_candidates = candidates + [bad]
            with pytest.raises(ValueError, match="Invalid ticket"):
                self.optimizer.optimize(test_candidates, portfolio_size=1)

    def test_lotto649_support(self):
        """Test Lotto 6/49 support (6 numbers, 1-49)."""
        optimizer = PortfolioOptimizer(max_number=49, numbers_per_ticket=6)
        candidates = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
            [19, 20, 21, 22, 23, 24],
            [25, 26, 27, 28, 29, 30],
        ]

        result = optimizer.optimize_lotto649(candidates, portfolio_size=3)
        assert len(result.selected_tickets) == 3
        for ticket in result.selected_tickets:
            assert len(ticket) == 6

    def test_dailygrand_support(self):
        """Test Daily Grand support (5 numbers, 1-49)."""
        optimizer = PortfolioOptimizer(max_number=49, numbers_per_ticket=5)
        candidates = [
            [1, 2, 3, 4, 5],
            [6, 7, 8, 9, 10],
            [11, 12, 13, 14, 15],
            [16, 17, 18, 19, 20],
            [21, 22, 23, 24, 25],
        ]

        result = optimizer.optimize_dailygrand(candidates, portfolio_size=3)
        assert len(result.selected_tickets) == 3
        for ticket in result.selected_tickets:
            assert len(ticket) == 5

    def test_optimized_score_better_than_baseline(self):
        """Test that optimized portfolio score >= simple first-N baseline."""
        # Generate 50 unique candidates
        candidates = []
        for i in range(1, 51):
            ticket = list(range(i, i + 6))
            if max(ticket) <= 49:
                candidates.append(ticket)

        # Take first 20 as baseline (relatively clustered)
        # The remaining candidates provide more diversity
        portfolio_size = 15  # Less than candidate_count

        # Baseline: first 15 candidates
        baseline = candidates[:portfolio_size]
        scorer = PortfolioScorer(max_number=49, numbers_per_ticket=6)
        baseline_score = scorer.score(baseline)

        # Optimize using all candidates
        optimizer = PortfolioOptimizer(max_number=49, numbers_per_ticket=6)
        result = optimizer.optimize(candidates, portfolio_size=portfolio_size)

        # Optimized score should be >= baseline score
        assert result.portfolio_score.score >= baseline_score.score

    def test_candidate_input_not_mutated(self):
        """Test that input candidates are not mutated."""
        original_candidates = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
        ]
        candidates_copy = copy.deepcopy(original_candidates)

        self.optimizer.optimize(original_candidates, portfolio_size=3)

        assert original_candidates == candidates_copy

    def test_result_contains_metadata(self):
        """Test that result contains expected metadata."""
        candidates = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
        ]

        result = self.optimizer.optimize(candidates, portfolio_size=3, seed=42)

        assert result.candidate_count == 3
        assert result.portfolio_size == 3
        assert result.seed == 42
        assert result.algorithm == "greedy_forward_selection"
        assert result.converged is True
        assert result.portfolio_score is not None

    def test_optimize_portfolio_convenience_function(self):
        """Test the convenience function optimize_portfolio."""
        candidates = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
        ]

        result = optimize_portfolio(
            candidates,
            portfolio_size=3,
            max_number=49,
            numbers_per_ticket=6,
            seed=42
        )

        assert len(result.selected_tickets) == 3
        assert result.portfolio_size == 3
        assert result.seed == 42

    def test_duplicate_candidates_deduplicated(self):
        """Test that duplicate candidates are removed."""
        candidates = [
            [1, 2, 3, 4, 5, 6],
            [1, 2, 3, 4, 5, 6],  # Duplicate
            [7, 8, 9, 10, 11, 12],
            [7, 8, 9, 10, 11, 12],  # Duplicate
            [13, 14, 15, 16, 17, 18],
        ]

        result = self.optimizer.optimize(candidates, portfolio_size=3)

        assert result.candidate_count == 3
        assert len(result.selected_tickets) == 3

    def test_empty_candidates_raises_error(self):
        """Test that empty candidates raises ValueError."""
        with pytest.raises(ValueError, match="No valid candidates provided"):
            self.optimizer.optimize([], portfolio_size=3)

    def test_unsorted_ticket_accepted_and_normalized(self):
        """Test that unsorted but otherwise valid tickets are accepted."""
        candidates = [
            [6, 5, 4, 3, 2, 1],  # Unsorted but valid
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
            [19, 20, 21, 22, 23, 24],
            [25, 26, 27, 28, 29, 30],
        ]

        result = self.optimizer.optimize(candidates, portfolio_size=5)

        # First ticket should be normalized to sorted order
        assert result.selected_tickets[0] == (1, 2, 3, 4, 5, 6)

    def test_duplicate_numbers_rejected(self):
        """Test that tickets with duplicate numbers are rejected."""
        candidates = [
            [1, 2, 3, 4, 5, 5],  # Duplicate numbers
        ]

        with pytest.raises(ValueError, match="Invalid ticket"):
            self.optimizer.optimize(candidates, portfolio_size=1)

    def test_result_immutable(self):
        """Test that PortfolioOptimizerResult is immutable."""
        candidates = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
        ]

        result = self.optimizer.optimize(candidates, portfolio_size=3)

        # Verify selected_tickets is a tuple
        assert isinstance(result.selected_tickets, tuple)
        # Verify individual tickets are tuples
        for ticket in result.selected_tickets:
            assert isinstance(ticket, tuple)

        # Verify we can't modify the result
        with pytest.raises(Exception):
            result.selected_tickets = []  # type: ignore

        # Verify the result object itself is frozen
        with pytest.raises(Exception):
            result.converged = False  # type: ignore

    def test_different_max_number(self):
        """Test with different max_number."""
        optimizer = PortfolioOptimizer(max_number=10, numbers_per_ticket=3)
        candidates = [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
            [1, 2, 4],
            [3, 5, 7],
        ]

        result = optimizer.optimize(candidates, portfolio_size=3)
        assert len(result.selected_tickets) == 3
        for ticket in result.selected_tickets:
            assert len(ticket) == 3
            assert all(1 <= n <= 10 for n in ticket)

    def test_default_portfolio_size_works(self):
        """Test that default portfolio_size=33 works with enough candidates."""
        candidates = []
        for i in range(1, 40):
            ticket = list(range(i, i + 6))
            if max(ticket) <= 49:
                candidates.append(ticket)

        # Ensure we have at least 33 candidates
        assert len(candidates) >= 33

        result = self.optimizer.optimize(candidates)
        assert len(result.selected_tickets) == 33
        assert result.portfolio_size == 33
