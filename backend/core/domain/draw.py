"""Domain model for Draw - pure business logic, no database dependencies."""

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

@dataclass
class Draw:
    """Domain representation of a lottery draw."""
    
    draw_date: date
    numbers: List[int]
    id: Optional[int] = None
    bonus: Optional[int] = None
    jackpot_amount: Optional[float] = None
    total_sales: Optional[float] = None
    lottery_type: str = "6/49"
    
    def __post_init__(self):
        """Validate data after initialization."""
        if len(self.numbers) != 6:
            raise ValueError("Draw must have exactly 6 numbers")
        if not all(1 <= n <= 49 for n in self.numbers):
            raise ValueError("Numbers must be between 1 and 49")
        if len(set(self.numbers)) != 6:
            raise ValueError("Numbers must be unique")
        if self.bonus and not (1 <= self.bonus <= 49):
            raise ValueError("Bonus number must be between 1 and 49")
    
    def contains_number(self, number: int) -> bool:
        """Check if a number is in the draw."""
        return number in self.numbers
    
    def matches(self, ticket_numbers: List[int]) -> int:
        """Count matches with a ticket."""
        return len(set(self.numbers) & set(ticket_numbers))
    
    @property
    def sorted_numbers(self) -> List[int]:
        """Return sorted numbers."""
        return sorted(self.numbers)
    
    @property
    def sum_numbers(self) -> int:
        """Sum of all numbers."""
        return sum(self.numbers)
