"""Strategy endpoints."""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_strategies():
    """Get all available strategies."""
    return {
        "strategies": [
            {
                "id": 1,
                "name": "Random (Quick Pick)",
                "description": "Random number generation",
                "algorithm_type": "random"
            },
            {
                "id": 2,
                "name": "Sobol Sequence",
                "description": "Low-discrepancy sequence",
                "algorithm_type": "sobol"
            },
            {
                "id": 3,
                "name": "Monte Carlo Optimized",
                "description": "Monte Carlo simulation",
                "algorithm_type": "monte_carlo"
            },
            {
                "id": 4,
                "name": "Genetic Algorithm",
                "description": "Evolutionary algorithm",
                "algorithm_type": "genetic"
            },
            {
                "id": 5,
                "name": "Hybrid AI",
                "description": "Combined methods",
                "algorithm_type": "hybrid"
            }
        ]
    }

@router.get("/{strategy_id}")
async def get_strategy(strategy_id: int):
    """Get a specific strategy."""
    strategies = {
        1: {"id": 1, "name": "Random (Quick Pick)", "description": "Random number generation"},
        2: {"id": 2, "name": "Sobol Sequence", "description": "Low-discrepancy sequence"},
        3: {"id": 3, "name": "Monte Carlo Optimized", "description": "Monte Carlo simulation"},
        4: {"id": 4, "name": "Genetic Algorithm", "description": "Evolutionary algorithm"},
        5: {"id": 5, "name": "Hybrid AI", "description": "Combined methods"}
    }
    
    if strategy_id not in strategies:
        return {"error": "Strategy not found"}
    
    return strategies[strategy_id]
