"""Authentication service."""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException, status

from backend.database.base import sync_engine
from backend.models import User
from backend.config.settings import settings

# JWT settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return check_password_hash(hashed_password, plain_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return generate_password_hash(password, method='pbkdf2:sha256:260000')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            print(f"User not found: {username}")
            return None
        if not verify_password(password, user.hashed_password):
            print(f"Password verification failed for: {username}")
            return None
        print(f"User authenticated: {username}")
        return user
    except Exception as e:
        print(f"Authentication error: {e}")
        return None
    finally:
        session.close()

def get_current_user(token: str) -> User:
    """Get current user from JWT token."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = session.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    finally:
        session.close()
