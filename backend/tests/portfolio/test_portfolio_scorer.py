"""Tests for LottoLab portfolio structural scoring."""

import pytest

from backend.services.portfolio_scorer import (
    PortfolioScorer,
)


def test_rejects_empty_portfolio():
    scorer = PortfolioScorer()

    with pytest.raises(
        ValueError,
        match="At least one ticket",
    ):
        scorer.score([])


def test_rejects_duplicate_ticket():
    scorer = PortfolioScorer()

    ticket = (1, 2, 3, 4, 5, 6)

    with pytest.raises(
        ValueError,
        match="Duplicate tickets",
    ):
        scorer.score([
            ticket,
            ticket,
        ])


def test_rejects_duplicate_numbers_inside_ticket():
    scorer = PortfolioScorer()

    with pytest.raises(
        ValueError,
        match="duplicate numbers",
    ):
        scorer.score([
            (1, 1, 2, 3, 4, 5),
        ])


def test_rejects_number_outside_game_range():
    scorer = PortfolioScorer()

    with pytest.raises(
        ValueError,
        match="outside",
    ):
        scorer.score([
            (1, 2, 3, 4, 5, 50),
        ])


def test_disjoint_tickets_have_zero_overlap():
    scorer = PortfolioScorer()

    result = scorer.score([
        (1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12),
    ])

    assert result.average_pairwise_overlap == 0
    assert result.maximum_pairwise_overlap == 0
    assert result.unique_numbers_used == 12


def test_repeated_pairs_are_detected():
    scorer = PortfolioScorer()

    result = scorer.score([
        (1, 2, 3, 4, 5, 6),
        (1, 2, 7, 8, 9, 10),
    ])

    assert result.repeated_pair_count >= 1
    assert result.maximum_pairwise_overlap == 2


def test_repeated_triplets_are_detected():
    scorer = PortfolioScorer()

    result = scorer.score([
        (1, 2, 3, 4, 5, 6),
        (1, 2, 3, 7, 8, 9),
    ])

    assert result.repeated_triplet_count >= 1
    assert result.maximum_pairwise_overlap == 3


def test_full_number_coverage_is_measured():
    scorer = PortfolioScorer(
        max_number=12,
        numbers_per_ticket=6,
    )

    result = scorer.score([
        (1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12),
    ])

    assert result.coverage_ratio == 1.0
    assert result.unique_numbers_used == 12


def test_more_diverse_portfolio_scores_higher():
    scorer = PortfolioScorer()

    concentrated = scorer.score([
        (1, 2, 3, 4, 5, 6),
        (1, 2, 3, 4, 5, 7),
        (1, 2, 3, 4, 6, 7),
    ])

    diverse = scorer.score([
        (1, 2, 3, 4, 5, 6),
        (7, 8, 9, 10, 11, 12),
        (13, 14, 15, 16, 17, 18),
    ])

    assert diverse.score > concentrated.score


def test_daily_grand_main_ticket_supported():
    scorer = PortfolioScorer(
        max_number=49,
        numbers_per_ticket=5,
    )

    result = scorer.score([
        (1, 10, 20, 30, 40),
        (2, 11, 21, 31, 41),
    ])

    assert result.ticket_count == 2
    assert result.unique_numbers_used == 10
