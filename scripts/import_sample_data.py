"""Import sample lottery data for testing."""

import sys
from pathlib import Path
from datetime import date, timedelta
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.base import sync_engine
from backend.models import Draw
from sqlalchemy.orm import sessionmaker

def generate_sample_draws():
    """Generate sample lottery draws."""
    draws = []
    start_date = date(2020, 1, 1)
    
    for i in range(100):  # Generate 100 draws
        draw_date = start_date + timedelta(days=i*7)  # Weekly draws
        # Generate 6 unique numbers between 1-49
        numbers = sorted(random.sample(range(1, 50), 6))
        bonus = random.randint(1, 49)
        
        draw = Draw(
            draw_date=draw_date,
            numbers=numbers,
            bonus=bonus,
            jackpot_amount=random.randint(1000000, 70000000),
            total_sales=random.randint(5000000, 20000000),
            lottery_type="6/49"
        )
        draws.append(draw)
    
    return draws

def main():
    """Import sample data."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    # Check existing data
    count = session.query(Draw).count()
    print(f"Current draws: {count}")
    
    if count < 10:
        print("Adding sample draws...")
        sample_draws = generate_sample_draws()
        session.add_all(sample_draws)
        session.commit()
        print(f"Added {len(sample_draws)} sample draws")
    else:
        print("Sufficient data exists. Skipping import.")
    
    # Show some stats
    total = session.query(Draw).count()
    latest = session.query(Draw).order_by(Draw.draw_date.desc()).first()
    print(f"Total draws in database: {total}")
    if latest:
        print(f"Latest draw: {latest.draw_date} - {latest.numbers}")

if __name__ == "__main__":
    main()
