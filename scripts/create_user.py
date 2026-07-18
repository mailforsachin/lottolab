"""Create initial admin user."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.base import sync_engine
from backend.models import User
from backend.services.auth_service import get_password_hash
from sqlalchemy.orm import sessionmaker
import getpass

def create_user():
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        # Check if user exists
        existing = session.query(User).filter(User.username == "admin").first()
        if existing:
            print("⚠️  Admin user already exists!")
            return
        
        # Get password from user
        print("🔐 Create Admin User")
        print("=" * 40)
        password = getpass.getpass("Enter admin password: ")
        confirm = getpass.getpass("Confirm password: ")
        
        if password != confirm:
            print("❌ Passwords do not match!")
            return
        
        if len(password) < 8:
            print("❌ Password must be at least 8 characters!")
            return
        
        # Create admin user
        admin = User(
            username="admin",
            hashed_password=get_password_hash(password),
            is_active=True
        )
        session.add(admin)
        session.commit()
        
        print("✅ Admin user created successfully!")
        print("   Username: admin")
        print("   Password: [hidden]")
        print("\n🔐 Please login at: https://lottolab.omchat.ovh/login")
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    create_user()
