#!/usr/bin/env python3
"""Tests for the read-only simulation draw adapter."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.algorithms.base import (
    DAILY_GRAND,
    LOTTO_649,
)
from backend.database.base import Base
from backend.models import Draw
from backend.services.simulation_draw_adapter import (
    SimulationDrawAdapter,
)


@pytest.fixture
def session():
    """Create an isolated in-memory database."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_lotto649_mapping(session):
    """6/49 main and bonus values map correctly."""
    draw = Draw(
        id=100,
        draw_date=date(2026, 1, 1),
        numbers=[1, 2, 3, 4, 5, 6],
        bonus=7,
        lottery_type="6/49",
    )

    target = (
        SimulationDrawAdapter.from_orm_draw(
            draw,
            LOTTO_649,
        )
    )

    assert target.draw.draw_id == 100
    assert target.draw.numbers == (
        1, 2, 3, 4, 5, 6
    )
    assert target.bonus_number == 7
    assert target.draw.grand_number is None


def test_daily_grand_mapping(session):
    """Daily Grand sixth stored value becomes Grand."""
    draw = Draw(
        id=200,
        draw_date=date(2026, 1, 1),
        numbers=[8, 14, 18, 35, 37, 5],
        bonus=5,
        lottery_type="Daily Grand",
    )

    target = (
        SimulationDrawAdapter.from_orm_draw(
            draw,
            DAILY_GRAND,
        )
    )

    assert target.draw.numbers == (
        8, 14, 18, 35, 37
    )
    assert target.draw.grand_number == 5
    assert target.bonus_number is None


def test_load_targets_orders_by_date_then_id(
    session,
):
    """Chronology must not depend on insertion order."""
    rows = [
        Draw(
            id=30,
            draw_date=date(2026, 1, 2),
            numbers=[7, 8, 9, 10, 11, 12],
            bonus=13,
            lottery_type="6/49",
        ),
        Draw(
            id=20,
            draw_date=date(2026, 1, 1),
            numbers=[2, 3, 4, 5, 6, 7],
            bonus=8,
            lottery_type="6/49",
        ),
        Draw(
            id=10,
            draw_date=date(2026, 1, 1),
            numbers=[1, 2, 3, 4, 5, 6],
            bonus=7,
            lottery_type="6/49",
        ),
    ]

    session.add_all(rows)
    session.commit()

    targets = (
        SimulationDrawAdapter.load_targets(
            session,
            LOTTO_649,
        )
    )

    assert [
        target.draw.draw_id
        for target in targets
    ] == [10, 20, 30]


def test_load_targets_filters_game(session):
    """Only the selected game's rows are loaded."""
    session.add_all(
        [
            Draw(
                id=1,
                draw_date=date(2026, 1, 1),
                numbers=[1, 2, 3, 4, 5, 6],
                bonus=7,
                lottery_type="6/49",
            ),
            Draw(
                id=2,
                draw_date=date(2026, 1, 2),
                numbers=[8, 9, 10, 11, 12, 3],
                bonus=3,
                lottery_type="Daily Grand",
            ),
        ]
    )
    session.commit()

    targets = (
        SimulationDrawAdapter.load_targets(
            session,
            LOTTO_649,
        )
    )

    assert len(targets) == 1
    assert targets[0].draw.draw_id == 1


def test_adapter_does_not_modify_rows(session):
    """Loading targets must leave ORM rows unchanged."""
    original_numbers = [
        8, 14, 18, 35, 37, 5
    ]

    draw = Draw(
        id=50,
        draw_date=date(2026, 1, 1),
        numbers=list(original_numbers),
        bonus=5,
        lottery_type="Daily Grand",
    )

    session.add(draw)
    session.commit()

    SimulationDrawAdapter.load_targets(
        session,
        DAILY_GRAND,
    )

    session.expire_all()

    persisted = session.get(Draw, 50)

    assert persisted.numbers == original_numbers
    assert persisted.bonus == 5
    assert not session.dirty
    assert not session.new
    assert not session.deleted


def test_rejects_missing_lotto_bonus():
    """6/49 requires its same-draw bonus."""
    draw = Draw(
        id=1,
        draw_date=date(2026, 1, 1),
        numbers=[1, 2, 3, 4, 5, 6],
        bonus=None,
        lottery_type="6/49",
    )

    with pytest.raises(
        ValueError,
        match="missing.*bonus",
    ):
        SimulationDrawAdapter.from_orm_draw(
            draw,
            LOTTO_649,
        )


def test_rejects_invalid_daily_grand_length():
    """Daily Grand requires exactly six stored values."""
    draw = Draw(
        id=1,
        draw_date=date(2026, 1, 1),
        numbers=[1, 2, 3, 4, 5],
        lottery_type="Daily Grand",
    )

    with pytest.raises(
        ValueError,
        match="expected 5 main numbers",
    ):
        SimulationDrawAdapter.from_orm_draw(
            draw,
            DAILY_GRAND,
        )


def test_rejects_invalid_grand_number():
    """Grand Number must be in the official 1..7 range."""
    draw = Draw(
        id=1,
        draw_date=date(2026, 1, 1),
        numbers=[1, 2, 3, 4, 5, 8],
        lottery_type="Daily Grand",
    )

    with pytest.raises(
        ValueError,
        match="outside 1..7",
    ):
        SimulationDrawAdapter.from_orm_draw(
            draw,
            DAILY_GRAND,
        )


def test_rejects_duplicate_main_numbers():
    """Malformed historical rows fail explicitly."""
    draw = Draw(
        id=1,
        draw_date=date(2026, 1, 1),
        numbers=[1, 1, 2, 3, 4, 5],
        bonus=6,
        lottery_type="6/49",
    )

    with pytest.raises(
        ValueError,
        match="duplicate",
    ):
        SimulationDrawAdapter.from_orm_draw(
            draw,
            LOTTO_649,
        )
