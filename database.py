from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import text

SQLITE_URL = "sqlite:///./votacao.db"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    """Create/upgrade database schema as needed."""
    # Create tables if not present
    SQLModel.metadata.create_all(engine)

    # Lightweight migrations
    with engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info('candidate')"))
            cols = [row[1] for row in result]  # row[1] is column name in SQLite PRAGMA
            if "photo_url" not in cols:
                conn.execute(text("ALTER TABLE candidate ADD COLUMN photo_url TEXT"))
        except Exception:
            # Best-effort; keep app running even if PRAGMA/ALTER not supported
            pass

        # Add voter_registration to votepermit and create uniqueness index per session
        try:
            result = conn.execute(text("PRAGMA table_info('votepermit')"))
            cols = [row[1] for row in result]
            if "voter_registration" not in cols:
                conn.execute(text("ALTER TABLE votepermit ADD COLUMN voter_registration TEXT"))
            # Unique index to ensure one matrícula per sessão (NULLs allowed for legacy rows)
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_votepermit_session_registration "
                    "ON votepermit (session_id, voter_registration)"
                )
            )
        except Exception:
            # Best-effort; if index creation fails, app logic still enforces uniqueness
            pass


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = Session(engine, expire_on_commit=False)
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
    with Session(engine, expire_on_commit=False) as session:
        yield session
