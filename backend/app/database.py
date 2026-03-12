"""
Database configuration.

Provides the SQLAlchemy engine, session factory, and a startup health check.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool
from app.config import settings

DATABASE_URL = settings.database_url

# Create engine with connection pooling
# pool_size=5: Keep 5 connections ready
# max_overflow=10: Allow 10 extra connections if needed
# pool_pre_ping=True: Test connection before using (catches dead connections)
# pool_recycle=3600: Recycle connections after 1 hour (Supabase closes idle connections)
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # Set to True to see SQL statements
)

# Session factory: Creates new database sessions (like creating a new transaction)
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,  # Manual control of commits
    autoflush=False,   # Don't auto-send queries
    expire_on_commit=True  # Clear objects after commit
)

# Base class for all ORM models
Base = declarative_base()


def get_db():
    """
    Dependency injection for FastAPI routes.
    Provides a database session that auto-closes after route completes.
    
    Usage in routes:
        @app.get("/customers")
        def get_customers(db: Session = Depends(get_db)):
            return db.query(Customer).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> None:
    """Fail fast during startup if the configured database is unreachable."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

