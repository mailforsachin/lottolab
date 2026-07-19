"""
Portfolio training snapshot model with authoritative boundary metadata.
"""

from dataclasses import dataclass
from datetime import date
from typing import Tuple, Optional

from backend.services.walk_forward_backtest import HistoricalDraw


@dataclass(frozen=True)
class PortfolioTrainingSnapshot:
    """
    Immutable training snapshot with authoritative boundary metadata.

    The training_cutoff_date MUST be derived from the exact database rows
    used for training - never inferred or fabricated.

    Attributes:
        draws: Tuple of HistoricalDraw objects used for training
        training_cutoff_date: Maximum draw_date from the exact training rows
        training_draw_count: Exact number of training observations supplied
    """
    draws: Tuple[HistoricalDraw, ...]
    training_cutoff_date: Optional[date]
    training_draw_count: int

    def __post_init__(self):
        """Validate that training_draw_count matches len(draws) when cutoff is set."""
        if self.training_cutoff_date is not None:
            if self.training_draw_count != len(self.draws):
                raise ValueError(
                    f"training_draw_count ({self.training_draw_count}) must equal "
                    f"len(draws) ({len(self.draws)}) when cutoff is set"
                )
