"""Script to create database tables."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from backend.database.base import sync_engine, Base
from backend.models import Draw

def main():
    """Create all tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=sync_engine)
    print("Tables created successfully!")
    
    # Show created tables using text() for raw SQL
    with sync_engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result]
        print(f"Tables in database: {tables}")

if __name__ == "__main__":
    main()
