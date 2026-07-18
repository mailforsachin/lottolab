"""Add initial strategies to database."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.base import sync_engine
from backend.models import Strategy
from sqlalchemy.orm import sessionmaker

strategies = [
    {
        "name": "Random (Quick Pick)",
        "description": "Random number generation",
        "algorithm_type": "random"
    },
    {
        "name": "Sobol Sequence",
        "description": "Low-discrepancy sequence",
        "algorithm_type": "sobol"
    },
    {
        "name": "Monte Carlo Optimized",
        "description": "Monte Carlo simulation",
        "algorithm_type": "monte_carlo"
    },
    {
        "name": "Genetic Algorithm",
        "description": "Evolutionary algorithm",
        "algorithm_type": "genetic"
    },
    {
        "name": "Hybrid AI",
        "description": "Combined methods",
        "algorithm_type": "hybrid"
    }
]

Session = sessionmaker(bind=sync_engine)
session = Session()

for strategy_data in strategies:
    existing = session.query(Strategy).filter(Strategy.name == strategy_data["name"]).first()
    if not existing:
        strategy = Strategy(**strategy_data)
        session.add(strategy)
        print(f"✅ Added strategy: {strategy_data['name']}")
    else:
        print(f"⏭️  Strategy already exists: {strategy_data['name']}")

session.commit()
session.close()
