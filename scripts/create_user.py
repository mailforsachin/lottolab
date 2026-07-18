"""Create initial admin user."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.base import sync_engine
from backend.models import User
from backend.services.auth_service import get_password_hash
from sqlalchemy.orm import sessionmaker

def create_user():
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    # Check if user exists
    existing = session.query(User).filter(User.username == "admin").first()
    if existing:
        print("⚠️  Admin user already exists!")
        return
    
    # Create admin user
    admin = User(
        username="admin",
        hashed_password=get_password_hash("hellyeah2026!"),
        is_active=True
    )
    session.add(admin)
    session.commit()
    
    print("✅ Admin user created successfully!")
    print("   Username: admin")
    print("   Password: hellyeah2026!")

if __name__ == "__main__":
    create_user()
