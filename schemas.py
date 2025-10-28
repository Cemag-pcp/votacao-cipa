from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models import SessionStatus


class SessionCreate(BaseModel):
    code: str = Field(..., example="2025.1")
    expected_votes: int = Field(ge=0, default=0)


class SessionRead(BaseModel):
    id: int
    code: str
    expected_votes: int
    status: SessionStatus
    start_time: Optional[datetime]
    end_time: Optional[datetime]

    class Config:
        from_attributes = True


class CandidateCreate(BaseModel):
    name: str
    registration: str
    commission_number: str


class CandidateRead(BaseModel):
    id: int
    name: str
    registration: str
    commission_number: str

    class Config:
        from_attributes = True


class PollWorkerCreate(BaseModel):
    name: str
    registration: str


class PollWorkerRead(BaseModel):
    id: int
    name: str
    registration: str

    class Config:
        from_attributes = True


class SessionStatusUpdate(BaseModel):
    status: SessionStatus


class PermitCreate(BaseModel):
    pass


class PermitRead(BaseModel):
    token: str
    issued_at: datetime

    class Config:
        from_attributes = True


class VoteRequest(BaseModel):
    candidate_id: int
    permit_token: str


class VoteRead(BaseModel):
    id: int
    candidate_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class VoteSummary(BaseModel):
    candidate_id: int
    candidate_name: str
    total_votes: int


class SessionOverview(SessionRead):
    total_votes: int
    remaining_expected_votes: int