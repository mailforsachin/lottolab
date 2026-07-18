"""Database base class and declarative base."""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from backend.config.settings import settings

# Use conventional naming for constraints to make migrations cleaner
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

# Async engine for FastAPI (async/await)
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("mysql+pymysql", "mysql+aiomysql"),
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync engine for Alembic migrations
sync_engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

# Sync session factory (for scripts)
SyncSessionLocal = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False,
)

async def get_async_session():
    """Dependency for getting async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
