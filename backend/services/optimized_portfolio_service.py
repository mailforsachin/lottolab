"""Database-independent structural portfolio construction.

This service composes an existing registered ticket-generation strategy with
the deterministic :class:`PortfolioOptimizer`.  It constructs portfolios from
the supplied training draws only; it does not accept target draws, evaluate
tickets, or use prize, ROI, or outcome information.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from backend.core.algorithms.base import (
    GameConfig,
    GeneratedTicket,
    ensure_unique_tickets,
)
from backend.core.algorithms.registry import get_strategy
from backend.services.portfolio_optimizer import (
    PortfolioOptimizer,
    PortfolioOptimizerResult,
)
from backend.services.walk_forward_backtest import HistoricalDraw


DEFAULT_PORTFOLIO_SIZE = 33
DEFAULT_CANDIDATE_MULTIPLIER = 10


@dataclass(frozen=True)
class OptimizedPortfolioResult:
    """Immutable output of reproducible structural portfolio construction."""

    strategy_id: int
    strategy_name: str
    game_name: str
    candidate_count: int
    unique_candidate_count: int
    portfolio_size: int
    seed: int
    selected_tickets: tuple[GeneratedTicket, ...]
    optimizer_result: PortfolioOptimizerResult


class OptimizedPortfolioService:
    """Build a structurally diverse portfolio from registered strategy output."""

    def __init__(
        self,
        candidate_multiplier: int = DEFAULT_CANDIDATE_MULTIPLIER,
    ) -> None:
        if (
            isinstance(candidate_multiplier, bool)
            or not isinstance(candidate_multiplier, int)
            or candidate_multiplier < 1
        ):
            raise ValueError("candidate_multiplier must be at least 1.")

        self.candidate_multiplier = candidate_multiplier

    def build(
        self,
        training_draws: Sequence[HistoricalDraw],
        strategy_id: int,
        game: GameConfig,
        portfolio_size: int = DEFAULT_PORTFOLIO_SIZE,
        candidate_count: int | None = None,
        seed: int = 0,
    ) -> OptimizedPortfolioResult:
        """Generate candidates and select a structural portfolio.

        A tuple snapshot of ``training_draws`` is passed to the registered
        strategy. They are the sole historical input to candidate generation;
        structural selection then considers only generated ticket combinations.
        """
        if (
            isinstance(portfolio_size, bool)
            or not isinstance(portfolio_size, int)
            or portfolio_size < 1
        ):
            raise ValueError("portfolio_size must be at least 1.")

        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer.")

        resolved_candidate_count = (
            portfolio_size * self.candidate_multiplier
            if candidate_count is None
            else candidate_count
        )

        if (
            isinstance(resolved_candidate_count, bool)
            or not isinstance(resolved_candidate_count, int)
            or resolved_candidate_count < portfolio_size
        ):
            raise ValueError(
                "candidate_count must be an integer at least portfolio_size."
            )

        game.validate()
        strategy = get_strategy(strategy_id)
        training_snapshot = tuple(training_draws)
        candidates = strategy.generate(
            training_draws=training_snapshot,
            ticket_count=resolved_candidate_count,
            game=game,
            seed=seed,
        )
        validated_candidates = ensure_unique_tickets(
            candidates,
            expected_count=resolved_candidate_count,
            game=game,
        )

        # Main-number combinations are the complete structural input.  The
        # first generated ticket for a combination is retained so that Daily
        # Grand rehydration preserves its associated Grand Number deterministically.
        ticket_by_numbers: dict[tuple[int, ...], GeneratedTicket] = {}
        for ticket in validated_candidates:
            ticket_by_numbers.setdefault(ticket.numbers, ticket)

        optimizer = PortfolioOptimizer(
            max_number=game.max_main_number,
            numbers_per_ticket=game.main_numbers_drawn,
        )
        optimizer_result = optimizer.optimize(
            candidates=[list(ticket.numbers) for ticket in validated_candidates],
            portfolio_size=portfolio_size,
            seed=seed,
        )

        selected_tickets = tuple(
            ticket_by_numbers[numbers]
            for numbers in optimizer_result.selected_tickets
        )

        return OptimizedPortfolioResult(
            strategy_id=strategy_id,
            strategy_name=strategy.name,
            game_name=game.name,
            candidate_count=resolved_candidate_count,
            unique_candidate_count=optimizer_result.candidate_count,
            portfolio_size=portfolio_size,
            seed=seed,
            selected_tickets=selected_tickets,
            optimizer_result=optimizer_result,
        )
