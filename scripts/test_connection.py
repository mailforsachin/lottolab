"""Script to test database connection."""

import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from backend.database.base import sync_engine
from backend.models import Draw
from sqlalchemy.orm import sessionmaker

def main():
    """Test database connection and create a test record."""
    with sync_engine.connect() as conn:
        # Test query using text()
        result = conn.execute(text("SELECT 1"))
        print("✓ Database connection successful!")
        
        # Check if tables exist
        result = conn.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result]
        print(f"✓ Tables: {tables}")
        
        # Create a test draw using ORM
        Session = sessionmaker(bind=sync_engine)
        session = Session()
        
        # Check if we already have data
        count = session.query(Draw).count()
        print(f"✓ Current draws in database: {count}")
        
        # Add a test draw if empty
        if count == 0:
            test_draw = Draw(
                draw_date=date(2024, 1, 1),
                numbers=[3, 14, 22, 31, 41, 47],
                bonus=34,
                jackpot_amount=50000000,
                total_sales=15000000,
                lottery_type="6/49"
            )
            session.add(test_draw)
            session.commit()
            print("✓ Added test draw!")
        
        # Show a sample
        sample = session.query(Draw).first()
        if sample:
            print(f"✓ Sample draw: {sample.draw_date} - {sample.numbers}")
            
        session.close()

if __name__ == "__main__":
    main()
