"""Leakage-safe simulation endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import sessionmaker

from backend.core.algorithms.base import DAILY_GRAND, LOTTO_649
from backend.database.base import sync_engine
from backend.models import SimulationRun
from backend.services.simulation_draw_adapter import SimulationDrawAdapter
from backend.services.simulation_service import SimulationService


router = APIRouter()

TICKET_PRICE = Decimal("3.00")
DEFAULT_TICKET_COUNT = 33
DEFAULT_TARGET_COUNT = 500
MINIMUM_TRAINING_DRAWS = 500


class SimulationRequest(BaseModel):
    """Request for a leakage-safe walk-forward simulation."""

    strategy_id: int = Field(ge=1, le=5)
    num_tickets: int = Field(
        default=DEFAULT_TICKET_COUNT,
        ge=1,
        le=1000,
    )
    game_type: str = "6/49"
    target_count: int = Field(
        default=DEFAULT_TARGET_COUNT,
        ge=1,
        le=5000,
    )
    seed: Optional[int] = None
    parameters: Optional[dict] = None


class SimulationResponse(BaseModel):
    """Simulation creation response."""

    id: int
    strategy_id: int
    total_tickets: int
    status: str
    game_type: str
    message: str


def resolve_game(game_type: str):
    """Resolve API game name to canonical game configuration."""

    normalized = game_type.strip().lower()

    if normalized in {
        "6/49",
        "649",
        "lotto649",
        "lotto 6/49",
    }:
        return LOTTO_649

    if normalized in {
        "dailygrand",
        "daily grand",
        "daily_grand",
    }:
        return DAILY_GRAND

    raise ValueError(
        "Unsupported game_type. "
        "Use '6/49' or 'dailygrand'."
    )


def _decimal_to_float(value):
    """Safely serialize optional Decimal values."""

    return float(value) if value is not None else 0.0


def run_simulation_task(
    simulation_id: int,
    strategy_id: int,
    num_tickets: int,
    game_type: str,
    target_count: int,
    seed: int | None,
) -> None:
    """Run a leakage-safe walk-forward simulation.

    The portfolio size represents tickets purchased for one target draw.

    Historical research may evaluate that same portfolio rule across
    many unseen historical targets. Historical evaluations must not be
    confused with actual gambling spend.
    """

    Session = sessionmaker(bind=sync_engine)
    session = Session()
    sim = None

    try:
        sim = (
            session.query(SimulationRun)
            .filter(
                SimulationRun.id == simulation_id
            )
            .first()
        )

        if sim is None:
            return

        sim.status = "running"
        sim.started_at = datetime.utcnow()
        session.commit()

        game = resolve_game(game_type)

        targets = SimulationDrawAdapter.load_targets(
            session=session,
            game=game,
        )

        service = SimulationService(
            minimum_training_draws=(
                MINIMUM_TRAINING_DRAWS
            )
        )

        result = service.run_walk_forward(
            targets=targets,
            strategy_id=strategy_id,
            ticket_count=num_tickets,
            game=game,
            seed=seed,
            max_targets=target_count,
        )

        portfolio_cost = (
            Decimal(num_tickets)
            * TICKET_PRICE
        )

        research_cost = result.total_cost(
            TICKET_PRICE
        )

        research_roi = result.roi(
            TICKET_PRICE
        )

        best_win = max(
            (
                item.evaluation.prize
                for target_result
                in result.target_results
                for item
                in target_result.tickets
            ),
            default=Decimal("0"),
        )

        parameters = dict(
            sim.parameters or {}
        )

        parameters.update(
            {
                "methodology": "walk_forward",
                "leakage_safe": True,
                "strategy_name": (
                    result.strategy_name
                ),
                "ticket_price": float(
                    TICKET_PRICE
                ),
                "tickets_per_target": (
                    num_tickets
                ),
                "portfolio_cost": float(
                    portfolio_cost
                ),
                "target_count": (
                    result.target_count
                ),
                "historical_ticket_evaluations": (
                    result.total_ticket_purchases
                ),
                "research_total_cost": float(
                    research_cost
                ),
                "seed": seed,
                "minimum_training_draws": (
                    MINIMUM_TRAINING_DRAWS
                ),
                "cost_interpretation": (
                    "portfolio_cost is the cost of "
                    "one ticket portfolio for one "
                    "draw; research_total_cost is "
                    "a hypothetical historical "
                    "backtest denominator and is "
                    "not actual gambling spend"
                ),
            }
        )

        sim.status = "completed"
        sim.completed_at = datetime.utcnow()

        # Backward-compatible field:
        # represents tickets in ONE portfolio,
        # not all historical evaluations.
        sim.total_tickets = num_tickets

        # Backward-compatible field:
        # represents ONE portfolio's cost.
        sim.total_cost = portfolio_cost

        # Aggregate historical research winnings.
        sim.total_won = result.total_won

        # ROI is explicitly historical walk-forward
        # research ROI, not a prediction.
        sim.roi = research_roi

        sim.best_win = best_win
        sim.parameters = parameters

        session.commit()

        print(
            "Simulation "
            f"{simulation_id} completed: "
            f"{result.strategy_name}, "
            f"{result.target_count} targets, "
            f"{num_tickets} tickets/target."
        )

    except Exception as exc:
        session.rollback()

        if sim is not None:
            sim.status = "failed"

            parameters = dict(
                sim.parameters or {}
            )

            parameters["error"] = str(exc)
            sim.parameters = parameters

            session.commit()

        print(
            f"Simulation {simulation_id} failed: "
            f"{type(exc).__name__}: {exc}"
        )

    finally:
        session.close()


@router.get("/")
async def get_simulations():
    """Return recent simulation runs."""

    Session = sessionmaker(bind=sync_engine)
    session = Session()

    try:
        simulations = (
            session.query(SimulationRun)
            .order_by(
                SimulationRun.id.desc()
            )
            .limit(10)
            .all()
        )

        return {
            "simulations": [
                {
                    "id": sim.id,
                    "strategy_id": (
                        sim.strategy_id
                    ),
                    "total_tickets": (
                        sim.total_tickets
                    ),
                    "total_cost": (
                        _decimal_to_float(
                            sim.total_cost
                        )
                    ),
                    "total_won": (
                        _decimal_to_float(
                            sim.total_won
                        )
                    ),
                    "roi": (
                        _decimal_to_float(
                            sim.roi
                        )
                    ),
                    "best_win": (
                        _decimal_to_float(
                            sim.best_win
                        )
                    ),
                    "status": sim.status,
                    "game_type": (
                        sim.game_type or "6/49"
                    ),
                    "parameters": (
                        sim.parameters or {}
                    ),
                    "started_at": (
                        sim.started_at.isoformat()
                        if sim.started_at
                        else None
                    ),
                    "completed_at": (
                        sim.completed_at.isoformat()
                        if sim.completed_at
                        else None
                    ),
                }
                for sim in simulations
            ]
        }

    finally:
        session.close()


@router.post(
    "/",
    response_model=SimulationResponse,
)
async def create_simulation(
    request: SimulationRequest,
    background_tasks: BackgroundTasks,
):
    """Create a leakage-safe walk-forward simulation."""

    try:
        game = resolve_game(
            request.game_type
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    canonical_game_type = (
        "6/49"
        if game.name == LOTTO_649.name
        else "dailygrand"
    )

    Session = sessionmaker(bind=sync_engine)
    session = Session()

    try:
        parameters = dict(
            request.parameters or {}
        )

        parameters.update(
            {
                "methodology": "walk_forward",
                "leakage_safe": True,
                "tickets_per_target": (
                    request.num_tickets
                ),
                "ticket_price": float(
                    TICKET_PRICE
                ),
                "portfolio_cost": float(
                    Decimal(
                        request.num_tickets
                    )
                    * TICKET_PRICE
                ),
                "requested_target_count": (
                    request.target_count
                ),
                "seed": request.seed,
            }
        )

        sim = SimulationRun(
            strategy_id=request.strategy_id,
            total_tickets=0,
            total_cost=0,
            total_won=0,
            status="pending",
            game_type=canonical_game_type,
            parameters=parameters,
        )

        session.add(sim)
        session.commit()
        session.refresh(sim)

        background_tasks.add_task(
            run_simulation_task,
            sim.id,
            request.strategy_id,
            request.num_tickets,
            canonical_game_type,
            request.target_count,
            request.seed,
        )

        return SimulationResponse(
            id=sim.id,
            strategy_id=request.strategy_id,
            total_tickets=request.num_tickets,
            status="pending",
            game_type=canonical_game_type,
            message=(
                "Leakage-safe walk-forward "
                "simulation created with "
                f"{request.num_tickets} tickets "
                "per target draw."
            ),
        )

    finally:
        session.close()


@router.get("/{simulation_id}")
async def get_simulation(
    simulation_id: int,
):
    """Return one simulation and research metadata."""

    Session = sessionmaker(bind=sync_engine)
    session = Session()

    try:
        sim = (
            session.query(SimulationRun)
            .filter(
                SimulationRun.id
                == simulation_id
            )
            .first()
        )

        if sim is None:
            raise HTTPException(
                status_code=404,
                detail="Simulation not found",
            )

        parameters = sim.parameters or {}

        return {
            "id": sim.id,
            "strategy_id": sim.strategy_id,
            "total_tickets": (
                sim.total_tickets
            ),
            "total_cost": (
                _decimal_to_float(
                    sim.total_cost
                )
            ),
            "total_won": (
                _decimal_to_float(
                    sim.total_won
                )
            ),
            "roi": (
                _decimal_to_float(
                    sim.roi
                )
            ),
            "best_win": (
                _decimal_to_float(
                    sim.best_win
                )
            ),
            "status": sim.status,
            "game_type": (
                sim.game_type or "6/49"
            ),
            "methodology": parameters.get(
                "methodology"
            ),
            "portfolio": {
                "tickets_per_target": (
                    parameters.get(
                        "tickets_per_target",
                        sim.total_tickets,
                    )
                ),
                "ticket_price": (
                    parameters.get(
                        "ticket_price",
                        float(TICKET_PRICE),
                    )
                ),
                "portfolio_cost": (
                    parameters.get(
                        "portfolio_cost",
                        _decimal_to_float(
                            sim.total_cost
                        ),
                    )
                ),
            },
            "research": {
                "target_count": (
                    parameters.get(
                        "target_count"
                    )
                ),
                "historical_ticket_evaluations": (
                    parameters.get(
                        "historical_ticket_evaluations"
                    )
                ),
                "research_total_cost": (
                    parameters.get(
                        "research_total_cost"
                    )
                ),
                "roi": (
                    _decimal_to_float(
                        sim.roi
                    )
                ),
                "interpretation": (
                    "Historical walk-forward "
                    "research only; not a "
                    "prediction of future returns."
                ),
            },
            "parameters": parameters,
            "started_at": (
                sim.started_at.isoformat()
                if sim.started_at
                else None
            ),
            "completed_at": (
                sim.completed_at.isoformat()
                if sim.completed_at
                else None
            ),
        }

    finally:
        session.close()
