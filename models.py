from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class SessionStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class VotingSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    expected_votes: int = Field(default=0, ge=0)
    status: SessionStatus = Field(default=SessionStatus.PLANNED)
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)

    candidates: list[Candidate] = Relationship(back_populates="session")
    poll_workers: list[PollWorker] = Relationship(back_populates="session")
    permits: list[VotePermit] = Relationship(back_populates="session")
    votes: list[Vote] = Relationship(back_populates="session")


class Candidate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    registration: str
    commission_number: str

    session_id: int = Field(foreign_key="votingsession.id")
    session: VotingSession = Relationship(back_populates="candidates")
    votes: list[Vote] = Relationship(back_populates="candidate")


class PollWorker(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    registration: str

    session_id: int = Field(foreign_key="votingsession.id")
    session: VotingSession = Relationship(back_populates="poll_workers")


class VotePermit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    used_at: Optional[datetime] = Field(default=None)
    used: bool = Field(default=False)

    session_id: int = Field(foreign_key="votingsession.id")
    session: VotingSession = Relationship(back_populates="permits")
    vote: Optional[Vote] = Relationship(back_populates="permit")


class Vote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    session_id: int = Field(foreign_key="votingsession.id")
    session: VotingSession = Relationship(back_populates="votes")

    candidate_id: int = Field(foreign_key="candidate.id")
    candidate: Candidate = Relationship(back_populates="votes")

    permit_id: int = Field(foreign_key="votepermit.id", unique=True)
    permit: VotePermit = Relationship(back_populates="vote")