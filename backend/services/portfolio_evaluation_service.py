"""
Portfolio evaluation service - leakage-safe historical evaluation of fixed saved portfolios.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.models.draw import Draw
from backend.models.saved_portfolio import SavedPortfolio, SavedPortfolioTicket
from backend.core.algorithms.base import GameConfig, LOTTO_649, DAILY_GRAND


@dataclass(frozen=True)
class TicketMatchResult:
    """Match result for a single ticket."""
    position: int
    numbers: Tuple[int, ...]
    grand_number: Optional[int]
    main_matches: int
    grand_matches: int
    draw_id: int
    draw_date: str


@dataclass(frozen=True)
class DrawEvaluationResult:
    """Evaluation result for a single draw."""
    draw_id: int
    draw_date: str
    ticket_results: List[TicketMatchResult]
    best_main_matches: int
    grand_match_count: int


@dataclass(frozen=True)
class PortfolioEvaluationResult:
    """Complete evaluation result for a saved portfolio."""
    portfolio_id: int
    game: str
    cutoff_date: str
    evaluated_draw_count: int
    date_range: Tuple[str, str]
    draw_results: List[DrawEvaluationResult]
    match_distribution: Dict[int, int]
    best_main_matches: int
    best_main_match_draws: List[int]
    grand_match_distribution: Optional[Dict[int, int]]
    total_tickets: int


class PortfolioEvaluationService:
    """Read-only evaluation service for saved portfolios."""

    def __init__(self, session: Session):
        self.session = session

    def evaluate_portfolio(self, portfolio: SavedPortfolio) -> PortfolioEvaluationResult:
        """
        Evaluate a saved portfolio against eligible later draws.

        Evaluation is read-only and deterministic. The same portfolio will
        always produce the same evaluation result.

        Args:
            portfolio: Saved portfolio with verified training_cutoff_date

        Returns:
            PortfolioEvaluationResult with descriptive match statistics

        Raises:
            ValueError: If training_cutoff_date is None
        """
        if portfolio.training_cutoff_date is None:
            raise ValueError(
                "Portfolio lacks verified training boundary metadata. "
                "Only portfolios generated with the current version can be evaluated."
            )

        game_type = portfolio.game_type
        has_grand = game_type == "Daily Grand"
        cutoff = portfolio.training_cutoff_date

        # Get eligible draws - temporal query with deterministic order
        # WHERE lottery_type = game_type AND draw_date > cutoff
        # ORDER BY draw_date ASC, id ASC
        eligible_draws = self.session.query(Draw).filter(
            and_(
                Draw.lottery_type == game_type,
                Draw.draw_date > cutoff
            )
        ).order_by(
            Draw.draw_date.asc(),
            Draw.id.asc()
        ).all()

        # Get tickets ordered by position
        tickets = sorted(portfolio.tickets, key=lambda t: t.position)

        if not eligible_draws:
            return self._empty_result(portfolio, cutoff)

        draw_results = []
        match_distribution = {}
        best_main_matches = 0
        best_main_match_draws = []
        grand_match_distribution = {} if has_grand else None

        # Track total evaluations for invariant
        total_evaluations = len(tickets) * len(eligible_draws)

        for draw in eligible_draws:
            draw_result, draw_best_main, draw_grand_count = self._evaluate_draw(
                draw, tickets, has_grand
            )
            draw_results.append(draw_result)

            # Accumulate match distribution
            for ticket_result in draw_result.ticket_results:
                matches = ticket_result.main_matches
                match_distribution[matches] = match_distribution.get(matches, 0) + 1

                # Track best matches
                if matches > best_main_matches:
                    best_main_matches = matches
                    best_main_match_draws = [draw.id]
                elif matches == best_main_matches and matches > 0:
                    best_main_match_draws.append(draw.id)

            # Accumulate grand match distribution
            if has_grand and grand_match_distribution is not None:
                grand_match_distribution[draw_grand_count] = (
                    grand_match_distribution.get(draw_grand_count, 0) + 1
                )

        # Verify match_distribution invariant
        actual_total = sum(match_distribution.values())
        if actual_total != total_evaluations:
            raise RuntimeError(
                f"Match distribution invariant violated: "
                f"sum={actual_total}, expected={total_evaluations} "
                f"(tickets={len(tickets)}, draws={len(eligible_draws)})"
            )

        date_range = (
            eligible_draws[0].draw_date.isoformat(),
            eligible_draws[-1].draw_date.isoformat()
        )

        return PortfolioEvaluationResult(
            portfolio_id=portfolio.id,
            game=game_type,
            cutoff_date=cutoff.isoformat(),
            evaluated_draw_count=len(eligible_draws),
            date_range=date_range,
            draw_results=draw_results,
            match_distribution=match_distribution,
            best_main_matches=best_main_matches,
            best_main_match_draws=best_main_match_draws,
            grand_match_distribution=grand_match_distribution,
            total_tickets=len(tickets)
        )

    def _evaluate_draw(self, draw: Draw, tickets: List[SavedPortfolioTicket],
                       has_grand: bool) -> Tuple[DrawEvaluationResult, int, int]:
        """Evaluate a single draw against all tickets."""
        ticket_results = []
        best_main_matches = 0
        grand_match_count = 0

        # Extract main numbers from draw
        # For Daily Grand, main numbers are first 5
        if has_grand:
            # Daily Grand: numbers array is [n1, n2, n3, n4, n5, grand]
            draw_main_numbers = draw.numbers[:5] if draw.numbers else []
        else:
            draw_main_numbers = draw.numbers

        draw_numbers = set(draw_main_numbers)
        draw_grand = draw.bonus if has_grand else None

        for ticket in tickets:
            ticket_numbers = set(ticket.numbers)
            main_matches = len(ticket_numbers & draw_numbers)

            grand_matches = 0
            if has_grand and draw_grand is not None and ticket.grand_number is not None:
                grand_matches = 1 if ticket.grand_number == draw_grand else 0
                if grand_matches:
                    grand_match_count += 1

            ticket_result = TicketMatchResult(
                position=ticket.position,
                numbers=tuple(ticket.numbers),
                grand_number=ticket.grand_number,
                main_matches=main_matches,
                grand_matches=grand_matches,
                draw_id=draw.id,
                draw_date=draw.draw_date.isoformat()
            )
            ticket_results.append(ticket_result)

            if main_matches > best_main_matches:
                best_main_matches = main_matches

        return DrawEvaluationResult(
            draw_id=draw.id,
            draw_date=draw.draw_date.isoformat(),
            ticket_results=ticket_results,
            best_main_matches=best_main_matches,
            grand_match_count=grand_match_count
        ), best_main_matches, grand_match_count

    def _empty_result(self, portfolio: SavedPortfolio, cutoff) -> PortfolioEvaluationResult:
        """Return empty result when no eligible draws exist."""
        return PortfolioEvaluationResult(
            portfolio_id=portfolio.id,
            game=portfolio.game_type,
            cutoff_date=cutoff.isoformat(),
            evaluated_draw_count=0,
            date_range=("", ""),
            draw_results=[],
            match_distribution={},
            best_main_matches=0,
            best_main_match_draws=[],
            grand_match_distribution={} if portfolio.game_type == "Daily Grand" else None,
            total_tickets=len(portfolio.tickets)
        )
