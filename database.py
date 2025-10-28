from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

SQLITE_URL = "sqlite:///./votacao.db"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    """Create database tables if they do not already exist."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a database session."""
    with Session(engine) as session:
        yield session