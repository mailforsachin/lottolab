"""
Portfolio generation API endpoints.

Provides endpoints for generating structurally diversified lottery portfolios
using multiple strategies.
"""

from typing import List, Optional, Dict, Any, Tuple, Set
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError
from sqlalchemy.orm import Session
from datetime import date

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
from backend.models.portfolio_training import PortfolioTrainingSnapshot

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
    training_cutoff_date: Optional[str] = Field(
        None,
        description="Latest draw date included in training data (authoritative)"
    )
    training_draw_count: Optional[int] = Field(
        None,
        description="Exact number of training observations used"
    )
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

        # Load training draws with authoritative metadata using snapshot method
        adapter = PortfolioTrainingDrawAdapter(db)
        training_snapshot = adapter.load_training_snapshot(
            lottery_type=request.game_type,
            game=game_config
        )

        if not training_snapshot.draws:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No training data found for game: {request.game_type}"
            )

        # Build portfolio using MultiStrategyPortfolioService
        service = MultiStrategyPortfolioService()
        result = service.build_portfolio(
            training_snapshot=training_snapshot,
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
        training_cutoff_date=result.training_cutoff_date.isoformat()
            if result.training_cutoff_date else None,
        training_draw_count=result.training_draw_count,
        version="1.0.0"
    )

# ============================================
# Authenticated Persistence Endpoints
# ============================================

from backend.services.portfolio_persistence_service import PortfolioPersistenceService
from backend.models.user import User
from backend.services.auth_service import get_current_user
from backend.core.algorithms.base import LOTTO_649, DAILY_GRAND
from backend.core.algorithms.registry import available_strategies


class SavePortfolioRequest(BaseModel):
    """Request model for saving a portfolio snapshot."""
    game: str = Field(..., description="Game type: '6/49' or 'Daily Grand'")
    portfolio_size: int = Field(..., ge=1)
    selected_tickets: List[TicketResponse] = Field(..., min_length=1)
    strategy_ids: List[int] = Field(...)
    strategy_names: List[str] = Field(...)
    requested_candidate_count: int = Field(..., ge=1)
    generated_candidate_count: int = Field(..., ge=1)
    unique_structural_candidate_count: int = Field(..., ge=1)
    master_seed: int = Field(..., ge=0)
    per_strategy_allocations: List[AllocationResponse] = Field(...)
    structural_optimizer_score: Optional[float] = None
    structural_optimizer_metrics: Optional[Dict[str, Any]] = None
    training_cutoff_date: Optional[str] = Field(
        None,
        description="Latest draw date included in training data (from generation)"
    )
    training_draw_count: Optional[int] = Field(
        None,
        description="Number of training observations used (from generation)"
    )
    version: str = Field(default="1.0.0")

    @model_validator(mode='after')
    def validate_candidate_counts(self) -> 'SavePortfolioRequest':
        """Validate candidate counts are coherent."""
        if self.generated_candidate_count < self.portfolio_size:
            raise ValueError(f"generated_candidate_count ({self.generated_candidate_count}) must be >= portfolio_size ({self.portfolio_size})")
        if self.unique_structural_candidate_count < self.portfolio_size:
            raise ValueError(f"unique_structural_candidate_count ({self.unique_structural_candidate_count}) must be >= portfolio_size ({self.portfolio_size})")
        if self.unique_structural_candidate_count > self.generated_candidate_count:
            raise ValueError(f"unique_structural_candidate_count ({self.unique_structural_candidate_count}) must be <= generated_candidate_count ({self.generated_candidate_count})")
        if len(self.strategy_ids) != len(self.strategy_names):
            raise ValueError(f"strategy_ids length ({len(self.strategy_ids)}) must equal strategy_names length ({len(self.strategy_names)})")
        return self

    model_config = {"extra": "forbid"}

    @field_validator('game')
    @classmethod
    def validate_game(cls, v: str) -> str:
        """Validate game type is supported."""
        if v not in GAME_CONFIGS:
            raise ValueError(f"Unsupported game type: {v}. Supported: 6/49, Daily Grand")
        return v

    @field_validator('selected_tickets')
    @classmethod
    def validate_ticket_count(cls, v: List[TicketResponse], info) -> List[TicketResponse]:
        """Validate ticket count matches portfolio_size."""
        portfolio_size = info.data.get('portfolio_size', 0)
        if len(v) != portfolio_size:
            raise ValueError(f"selected_tickets count ({len(v)}) must equal portfolio_size ({portfolio_size})")
        return v

    @field_validator('selected_tickets')
    @classmethod
    def validate_ticket_structure(cls, v: List[TicketResponse], info) -> List[TicketResponse]:
        """Validate ticket structure based on game type."""
        game_type = info.data.get('game')
        if not game_type:
            return v

        game_config = GAME_CONFIGS.get(game_type)
        if not game_config:
            return v

        for ticket in v:
            numbers = ticket.numbers
            if len(numbers) != game_config.main_numbers_drawn:
                raise ValueError(f"Ticket must have {game_config.main_numbers_drawn} numbers, got {len(numbers)}")

            # Check range and uniqueness
            if len(set(numbers)) != len(numbers):
                raise ValueError("Ticket numbers must be unique")

            for num in numbers:
                if num < 1 or num > game_config.max_main_number:
                    raise ValueError(f"Number {num} outside valid range 1-{game_config.max_main_number}")

            # Check grand number
            if game_config.grand_max is not None:
                # Daily Grand: must have grand_number
                if ticket.grand_number is None:
                    raise ValueError("Daily Grand ticket must have grand_number")
                if ticket.grand_number < 1 or ticket.grand_number > game_config.grand_max:
                    raise ValueError(f"Grand number {ticket.grand_number} outside valid range 1-{game_config.grand_max}")
            else:
                # Lotto 6/49: must NOT have grand_number
                if ticket.grand_number is not None:
                    raise ValueError("Lotto 6/49 tickets must not have grand_number")

        # Check structural uniqueness within portfolio
        seen = set()
        for ticket in v:
            key = tuple(sorted(ticket.numbers))
            if key in seen:
                raise ValueError(f"Duplicate structural ticket found: {key}")
            seen.add(key)

        return v


class SavePortfolioResponse(BaseModel):
    """Response model for saving a portfolio."""
    id: int
    created_at: str
    game_type: str
    portfolio_size: int
    ticket_count: int


class ListPortfoliosResponse(BaseModel):
    """Response model for listing portfolios."""
    portfolios: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class PortfolioDetailResponse(BaseModel):
    """Response model for portfolio detail."""
    id: int
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
    structural_optimizer_score: Optional[float]
    structural_optimizer_metrics: Optional[Dict[str, Any]]
    version: str
    created_at: str
    training_cutoff_date: Optional[str] = Field(
        None,
        description="Latest draw date included in training data (authoritative)"
    )
    training_draw_count: Optional[int] = Field(
        None,
        description="Exact number of training observations used"
    )


@router.post("/", response_model=SavePortfolioResponse)
def save_portfolio(
    request: SavePortfolioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SavePortfolioResponse:
    """
    Save a portfolio snapshot to the authenticated user's account.

    The snapshot must match the structure returned by POST /portfolios/generate.
    """
    try:
        service = PortfolioPersistenceService()
        portfolio = service.save_portfolio(
            session=db,
            user_id=current_user.id,
            snapshot=request.model_dump()
        )

        return SavePortfolioResponse(
            id=portfolio.id,
            created_at=portfolio.created_at.isoformat(),
            game_type=portfolio.game_type,
            portfolio_size=portfolio.portfolio_size,
            ticket_count=len(portfolio.tickets)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save portfolio"
        )


@router.get("/", response_model=ListPortfoliosResponse)
def list_portfolios(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ListPortfoliosResponse:
    """
    List saved portfolios for the authenticated user.
    """
    service = PortfolioPersistenceService()
    result = service.list_portfolios(
        session=db,
        user_id=current_user.id,
        limit=min(limit, 100),
        offset=max(offset, 0)
    )

    return ListPortfoliosResponse(**result)


@router.get("/{portfolio_id}", response_model=PortfolioDetailResponse)
def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> PortfolioDetailResponse:
    """
    Get a saved portfolio by ID.

    Returns 404 if the portfolio does not exist or belongs to another user.
    """
    service = PortfolioPersistenceService()
    portfolio = service.get_portfolio(
        session=db,
        portfolio_id=portfolio_id,
        user_id=current_user.id
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    return PortfolioDetailResponse(**portfolio)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a saved portfolio.

    Returns 404 if the portfolio does not exist or belongs to another user.
    """
    service = PortfolioPersistenceService()
    deleted = service.delete_portfolio(
        session=db,
        portfolio_id=portfolio_id,
        user_id=current_user.id
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    return None

# ============================================
# Portfolio Evaluation Endpoint
# ============================================

from backend.services.portfolio_evaluation_service import PortfolioEvaluationService


class EvaluatePortfolioResponse(BaseModel):
    """Response model for portfolio evaluation."""
    portfolio_id: int
    game: str
    cutoff_date: str
    evaluated_draw_count: int
    date_range: Tuple[str, str]
    match_distribution: Dict[int, int]
    best_main_matches: int
    best_main_match_draws: List[int]
    grand_match_distribution: Optional[Dict[int, int]] = None
    total_tickets: int


@router.post("/{portfolio_id}/evaluate", response_model=EvaluatePortfolioResponse)
def evaluate_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> EvaluatePortfolioResponse:
    """
    Evaluate a saved portfolio against eligible later historical draws.

    Requires:
    - Portfolio must have verified training_cutoff_date
    - Portfolio must be owned by the authenticated user
    - Evaluation is descriptive only (no prediction/ROI/prize optimization)
    """
    try:
        # Get and verify ownership
        service = PortfolioPersistenceService()
        portfolio = service.repository.get_by_id(db, portfolio_id, current_user.id)

        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )

        # Check training boundary
        if portfolio.training_cutoff_date is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This portfolio cannot be evaluated because it lacks verified training-boundary metadata. Only portfolios generated with the current version support evaluation."
            )

        # Evaluate
        eval_service = PortfolioEvaluationService(db)
        result = eval_service.evaluate_portfolio(portfolio)

        return EvaluatePortfolioResponse(
            portfolio_id=result.portfolio_id,
            game=result.game,
            cutoff_date=result.cutoff_date,
            evaluated_draw_count=result.evaluated_draw_count,
            date_range=result.date_range,
            match_distribution=result.match_distribution,
            best_main_matches=result.best_main_matches,
            best_main_match_draws=result.best_main_match_draws,
            grand_match_distribution=result.grand_match_distribution,
            total_tickets=result.total_tickets
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during evaluation"
        )
