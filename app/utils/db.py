from collections.abc import Generator

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

# Import models so their metadata is registered before create_all
# ruff: noqa: F401
from app import db_models
from app.settings import settings


def _build_engine() -> Engine:
    url = settings.DATABASE_URL
    is_sqlite = url.startswith("sqlite")

    engine_kwargs: dict = {
        "echo": settings.DEBUG,
        # Avoid stale connections in long-running apps (esp. behind load balancers)
        "pool_pre_ping": True,
    }

    if is_sqlite:
        # Needed for SQLite used within FastAPI (single-threaded writer)
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        # SQLite doesn't use real connection pooling; recycle irrelevant
    else:
        # Reasonable defaults for Postgres
        engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
        # Recycle connections periodically to avoid server-side timeouts (secs)
        engine_kwargs["pool_recycle"] = 1800  # 30 minutes

    return create_engine(url, **engine_kwargs)


engine: Engine = _build_engine()


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency to provide a short-lived DB session per request."""
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    """Drop all database tables and recreate them (destructive)."""
    SQLModel.metadata.drop_all(engine, checkfirst=True)
    SQLModel.metadata.create_all(engine)
