#!/usr/bin/env python3
"""Tests for canonical single-draw ticket evaluation."""

from decimal import Decimal

import pytest

from backend.core.algorithms.base import (
    DAILY_GRAND,
    LOTTO_649,
    GeneratedTicket,
)
from backend.services.ticket_evaluator import evaluate_ticket
from backend.services.walk_forward_backtest import HistoricalDraw


def test_lotto649_exact_six_matches():
    ticket = GeneratedTicket(
        numbers=(1, 2, 3, 4, 5, 6),
    )

    target = HistoricalDraw(
        draw_id=100,
        numbers=(1, 2, 3, 4, 5, 6),
    )

    result = evaluate_ticket(
        ticket,
        target,
        LOTTO_649,
        bonus_number=7,
    )

    assert result.main_matches == 6
    assert result.bonus_match is False
    assert result.prize == Decimal("5000000")


def test_lotto649_five_plus_bonus_uses_same_draw():
    ticket = GeneratedTicket(
        numbers=(1, 2, 3, 4, 5, 7),
    )

    target = HistoricalDraw(
        draw_id=101,
        numbers=(1, 2, 3, 4, 5, 6),
    )

    result = evaluate_ticket(
        ticket,
        target,
        LOTTO_649,
        bonus_number=7,
    )

    assert result.main_matches == 5
    assert result.bonus_match is True
    assert result.prize == Decimal("100000")


def test_lotto649_five_without_bonus():
    ticket = GeneratedTicket(
        numbers=(1, 2, 3, 4, 5, 8),
    )

    target = HistoricalDraw(
        draw_id=102,
        numbers=(1, 2, 3, 4, 5, 6),
    )

    result = evaluate_ticket(
        ticket,
        target,
        LOTTO_649,
        bonus_number=7,
    )

    assert result.main_matches == 5
    assert result.bonus_match is False
    assert result.prize == Decimal("1000")


def test_daily_grand_five_plus_grand():
    ticket = GeneratedTicket(
        numbers=(1, 2, 3, 4, 5),
        grand_number=7,
    )

    target = HistoricalDraw(
        draw_id=200,
        numbers=(1, 2, 3, 4, 5),
        grand_number=7,
    )

    result = evaluate_ticket(
        ticket,
        target,
        DAILY_GRAND,
    )

    assert result.main_matches == 5
    assert result.grand_match is True
    assert result.prize == Decimal("7000000")


def test_daily_grand_main_and_grand_are_same_target():
    ticket = GeneratedTicket(
        numbers=(1, 2, 3, 4, 20),
        grand_number=6,
    )

    target = HistoricalDraw(
        draw_id=201,
        numbers=(1, 2, 3, 4, 5),
        grand_number=7,
    )

    result = evaluate_ticket(
        ticket,
        target,
        DAILY_GRAND,
    )

    assert result.main_matches == 4
    assert result.grand_match is False
    assert result.prize == Decimal("500")


def test_daily_grand_grand_only():
    ticket = GeneratedTicket(
        numbers=(10, 11, 12, 13, 14),
        grand_number=7,
    )

    target = HistoricalDraw(
        draw_id=202,
        numbers=(1, 2, 3, 4, 5),
        grand_number=7,
    )

    result = evaluate_ticket(
        ticket,
        target,
        DAILY_GRAND,
    )

    assert result.main_matches == 0
    assert result.grand_match is True
    assert result.prize == Decimal("4")


def test_rejects_invalid_target_draw():
    ticket = GeneratedTicket(
        numbers=(1, 2, 3, 4, 5, 6),
    )

    target = HistoricalDraw(
        draw_id=300,
        numbers=(1, 1, 2, 3, 4, 5),
    )

    with pytest.raises(
        ValueError,
        match="duplicate",
    ):
        evaluate_ticket(
            ticket,
            target,
            LOTTO_649,
            bonus_number=7,
        )


def test_rejects_bonus_that_duplicates_main_number():
    ticket = GeneratedTicket(
        numbers=(1, 2, 3, 4, 5, 6),
    )

    target = HistoricalDraw(
        draw_id=301,
        numbers=(1, 2, 3, 4, 5, 6),
    )

    with pytest.raises(
        ValueError,
        match="cannot duplicate",
    ):
        evaluate_ticket(
            ticket,
            target,
            LOTTO_649,
            bonus_number=6,
        )
