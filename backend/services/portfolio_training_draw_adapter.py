"""
Read-only adapter for loading historical training observations for portfolio construction.

This adapter loads historical draw data from the database in deterministic chronological order,
validates main numbers against game configuration, and returns immutable HistoricalDraw objects
with authoritative boundary metadata.
"""

from typing import List, Tuple, Optional, Sequence
import json
from datetime import date
from sqlalchemy.orm import Session

from backend.models.draw import Draw
from backend.core.algorithms.base import GameConfig
from backend.services.walk_forward_backtest import HistoricalDraw
from backend.models.portfolio_training import PortfolioTrainingSnapshot


class PortfolioTrainingDrawAdapter:
    """
    Read-only adapter for loading historical training observations.

    Loads draws in deterministic chronological order (draw_date ASC, id ASC).
    Validates main numbers against canonical GameConfig.
    Preserves Grand Number for Daily Grand when available.
    Returns authoritative metadata with the training snapshot.
    """

    def __init__(self, session: Session):
        """
        Initialize the adapter with a database session.

        Args:
            session: SQLAlchemy session (read-only usage)
        """
        self.session = session

    def load_training_snapshot(
        self,
        lottery_type: str,
        game: GameConfig,
        limit: Optional[int] = None
    ) -> PortfolioTrainingSnapshot:
        """
        Load historical training draws with authoritative metadata.

        Args:
            lottery_type: The lottery type to load ("6/49" or "Daily Grand")
            game: GameConfig with validation rules
            limit: Optional limit on number of draws to load

        Returns:
            PortfolioTrainingSnapshot with draws and authoritative metadata

        Raises:
            ValueError: If lottery_type is unsupported or data is malformed
        """
        if lottery_type not in ["6/49", "Daily Grand"]:
            raise ValueError(f"Unsupported lottery type: {lottery_type}")

        # Build query - deterministic chronological order
        query = self.session.query(Draw).filter(
            Draw.lottery_type == lottery_type
        ).order_by(
            Draw.draw_date.asc(),
            Draw.id.asc()
        )

        if limit is not None:
            query = query.limit(limit)

        draws = query.all()

        if not draws:
            return PortfolioTrainingSnapshot(
                draws=(),
                training_cutoff_date=None,
                training_draw_count=0
            )

        historical_draws = []
        for draw in draws:
            # Extract main numbers
            numbers = self._extract_main_numbers(draw, game)

            # Validate main numbers
            if not self._validate_main_numbers(numbers, game):
                raise ValueError(
                    f"Invalid main numbers for draw {draw.draw_date}: {numbers}"
                )

            # Extract grand number if applicable
            grand_number = self._extract_grand_number(draw, lottery_type)

            # Create HistoricalDraw with authoritative draw_date
            historical_draws.append(HistoricalDraw(
                draw_id=draw.id,
                numbers=tuple(sorted(numbers)),
                grand_number=grand_number,
                draw_date=draw.draw_date.isoformat() if draw.draw_date else None
            ))

        # Authoritative metadata from exact database rows
        training_cutoff_date = max(draw.draw_date for draw in draws)
        training_draw_count = len(historical_draws)

        return PortfolioTrainingSnapshot(
            draws=tuple(historical_draws),
            training_cutoff_date=training_cutoff_date,
            training_draw_count=training_draw_count
        )

    def load_training_draws(
        self,
        lottery_type: str,
        game: GameConfig,
        limit: Optional[int] = None
    ) -> List[HistoricalDraw]:
        """
        Legacy method - returns only draws for backward compatibility.

        Args:
            lottery_type: The lottery type to load ("6/49" or "Daily Grand")
            game: GameConfig with validation rules
            limit: Optional limit on number of draws to load

        Returns:
            List of HistoricalDraw objects in chronological order

        Raises:
            ValueError: If lottery_type is unsupported or data is malformed
        """
        snapshot = self.load_training_snapshot(lottery_type, game, limit)
        return list(snapshot.draws)

    def _extract_main_numbers(self, draw: Draw, game: GameConfig) -> List[int]:
        """
        Extract main numbers from a draw.

        For Lotto 6/49: Uses all 6 numbers
        For Daily Grand: Uses first 5 numbers (main numbers)
        """
        if not draw.numbers:
            return []

        # Draw.numbers is stored as JSON
        if isinstance(draw.numbers, str):
            numbers = json.loads(draw.numbers)
        else:
            numbers = draw.numbers

        # For Daily Grand, main numbers are the first 5
        if draw.lottery_type == "Daily Grand":
            # Daily Grand stored as [n1, n2, n3, n4, n5, grand]
            return numbers[:5] if len(numbers) >= 5 else numbers

        # Lotto 6/49 uses all numbers
        return numbers[:game.main_numbers_drawn]

    def _extract_grand_number(self, draw: Draw, lottery_type: str) -> Optional[int]:
        """
        Extract grand number from a Daily Grand draw.
        """
        if lottery_type != "Daily Grand":
            return None

        if draw.bonus is not None:
            return draw.bonus

        # If bonus not set, try to extract from numbers
        if draw.numbers:
            if isinstance(draw.numbers, str):
                numbers = json.loads(draw.numbers)
            else:
                numbers = draw.numbers
            if len(numbers) >= 6:
                return numbers[5]

        return None

    def _validate_main_numbers(self, numbers: List[int], game: GameConfig) -> bool:
        """
        Validate main numbers against game configuration.

        Checks:
        - Correct number of main numbers
        - All numbers within range 1..max_main_number
        - All numbers are unique
        """
        if not numbers:
            return False

        if len(numbers) != game.main_numbers_drawn:
            return False

        # Check range and uniqueness
        seen = set()
        for num in numbers:
            if not isinstance(num, int):
                return False
            if num < 1 or num > game.max_main_number:
                return False
            if num in seen:
                return False
            seen.add(num)

        return True
