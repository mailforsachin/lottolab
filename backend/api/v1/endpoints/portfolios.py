"""
Portfolio generation API endpoints.

Provides endpoints for generating structurally diversified lottery portfolios
using multiple strategies.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, ValidationError
from sqlalchemy.orm import Session

from backend.database.base import SyncSessionLocal
from backend.core.algorithms.base import GameConfig, LOTTO_649, DAILY_GRAND
from backend.core.algorithms.registry import available_strategies
from backend.services.portfolio_training_draw_adapter import (
    PortfolioTrainingDrawAdapter,
)
from backend.services.multi_strategy_portfolio_service import (
    MultiStrategyPortfolioService,
    MultiStrategyPortfolioResult
)
from backend.services.portfolio_optimizer import PortfolioOptimizerResult

# Use canonical game configurations from base.py
GAME_CONFIGS = {
    "6/49": LOTTO_649,
    "Daily Grand": DAILY_GRAND,
}


class GeneratePortfolioRequest(BaseModel):
    """Request model for portfolio generation."""
    game_type: str = Field(..., description="Game type: '6/49' or 'Daily Grand'")
    portfolio_size: int = Field(33, ge=1, description="Number of tickets to select")
    candidate_count: int = Field(500, ge=1, description="Total candidates to generate")
    strategy_ids: Optional[List[int]] = Field(
        None,
        description="Strategy IDs to use (default: all registered)"
    )
    seed: int = Field(0, ge=0, description="Master seed for reproducibility")

    model_config = {
        "extra": "forbid"
    }

    @field_validator('game_type')
    @classmethod
    def validate_game_type(cls, v: str) -> str:
        """Validate game type is supported."""
        if v not in GAME_CONFIGS:
            raise ValueError(f"Unsupported game type: {v}. Supported: 6/49, Daily Grand")
        return v

    @field_validator('candidate_count')
    @classmethod
    def validate_candidate_count(cls, v: int, info) -> int:
        """Validate candidate_count >= portfolio_size."""
        portfolio_size = info.data.get('portfolio_size', 33)
        if v < portfolio_size:
            raise ValueError(f"candidate_count ({v}) must be >= portfolio_size ({portfolio_size})")
        return v

    @field_validator('strategy_ids')
    @classmethod
    def validate_strategy_ids(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        """Validate strategy IDs are registered."""
        if v is None:
            return v

        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate strategy IDs are not allowed")

        registered_ids = {s['id'] for s in available_strategies()}
        for sid in v:
            if sid not in registered_ids:
                raise ValueError(f"Unknown strategy ID: {sid}")
        return v


class TicketResponse(BaseModel):
    """Response model for a single ticket."""
    numbers: List[int]
    grand_number: Optional[int] = None
    strategy_ids: Optional[List[int]] = None
    strategy_names: Optional[List[str]] = None


class AllocationResponse(BaseModel):
    """Response model for per-strategy allocation."""
    strategy_id: int
    strategy_name: str
    requested: int
    generated: int
    derived_seed: int


class GeneratePortfolioResponse(BaseModel):
    """Response model for portfolio generation."""
    game: str
    portfolio_size: int
    selected_tickets: List[TicketResponse]
    strategy_ids: List[int]
    strategy_names: List[str]
    requested_candidate_count: int
    generated_candidate_count: int
    unique_structural_candidate_count: int
    master_seed: int
    per_strategy_allocations: List[AllocationResponse]
    structural_optimizer_score: Optional[float] = None
    structural_optimizer_metrics: Optional[Dict[str, Any]] = None
    version: str = "1.0.0"


router = APIRouter()


def get_db():
    """Get database session."""
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.post("/generate", response_model=GeneratePortfolioResponse)
def generate_portfolio(
    request: GeneratePortfolioRequest,
    db: Session = Depends(get_db)
) -> GeneratePortfolioResponse:
    """
    Generate a structurally diversified portfolio of lottery tickets.

    This endpoint:
    1. Loads historical training observations from the database
    2. Generates candidates using multiple strategies
    3. Structurally deduplicates candidates
    4. Selects a structurally diversified portfolio using greedy forward selection

    The portfolio is optimized for structural diversity, NOT for predicting
    future winning numbers.
    """
    try:
        # Resolve game configuration
        game_config = GAME_CONFIGS[request.game_type]

        # Load training draws
        adapter = PortfolioTrainingDrawAdapter(db)
        training_draws = adapter.load_training_draws(
            lottery_type=request.game_type,
            game=game_config
        )

        if not training_draws:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No training data found for game: {request.game_type}"
            )

        # Build portfolio using MultiStrategyPortfolioService
        service = MultiStrategyPortfolioService()
        result = service.build_portfolio(
            training_draws=training_draws,
            game=game_config,
            portfolio_size=request.portfolio_size,
            candidate_count=request.candidate_count,
            master_seed=request.seed,
            strategy_ids=request.strategy_ids
        )

        # Build response
        return _build_response(result, game_config)

    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio generation failed: {str(e)}"
        )
    except Exception as e:
        # Don't expose raw internal stack traces
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during portfolio generation"
        )


def _build_response(
    result: MultiStrategyPortfolioResult,
    game_config: GameConfig
) -> GeneratePortfolioResponse:
    """Build the API response from the service result."""
    # Build a map from numbers to provenance
    provenance_map = {}
    for prov in result.provenance:
        key = tuple(prov.numbers)
        provenance_map[key] = prov

    # Build selected tickets with their provenance
    selected_tickets = []
    for ticket in result.selected_tickets:
        key = tuple(ticket.numbers)
        prov = provenance_map.get(key)

        ticket_response = TicketResponse(
            numbers=list(ticket.numbers),
            grand_number=ticket.grand_number,
            strategy_ids=list(prov.strategy_ids) if prov else None,
            strategy_names=list(prov.strategy_names) if prov else None
        )
        selected_tickets.append(ticket_response)

    # Build allocations
    allocations = []
    for alloc in result.allocations:
        allocations.append(AllocationResponse(
            strategy_id=alloc.strategy_id,
            strategy_name=alloc.strategy_name,
            requested=alloc.requested,
            generated=alloc.generated,
            derived_seed=alloc.derived_seed
        ))

    # Extract optimizer score from the actual PortfolioOptimizerResult
    optimizer_score = None
    optimizer_metrics = None
    if result.optimizer_result and result.optimizer_result.portfolio_score:
        score_obj = result.optimizer_result.portfolio_score
        optimizer_score = score_obj.score
        optimizer_metrics = {
            "score": score_obj.score,
        }

    return GeneratePortfolioResponse(
        game=game_config.name,
        portfolio_size=result.portfolio_size,
        selected_tickets=selected_tickets,
        strategy_ids=list(result.strategy_ids),
        strategy_names=list(result.strategy_names),
        requested_candidate_count=result.requested_candidate_count,
        generated_candidate_count=result.generated_candidate_count,
        unique_structural_candidate_count=result.unique_structural_candidate_count,
        master_seed=result.master_seed,
        per_strategy_allocations=allocations,
        structural_optimizer_score=optimizer_score,
        structural_optimizer_metrics=optimizer_metrics,
        version="1.0.0"
    )
