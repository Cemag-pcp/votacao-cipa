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
    photo_url: Optional[str] = None

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
    # Matrícula do eleitor a ser autorizada
    voter_registration: str


class PermitRead(BaseModel):
    token: str
    issued_at: datetime

    class Config:
        from_attributes = True


class PermitListItem(BaseModel):
    token: str
    issued_at: datetime
    used: bool
    used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VoteRequest(BaseModel):
    candidate_id: Optional[int] = None
    null_vote: bool = False
    permit_token: str

    def validate(self):
        # Ensure exactly one of candidate_id or null_vote is provided
        has_candidate = self.candidate_id is not None
        if has_candidate == self.null_vote:
            raise ValueError("Provide either candidate_id or set null_vote true, not both")
        return self


class VoteRead(BaseModel):
    id: int
    candidate_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class VoteSummary(BaseModel):
    candidate_id: Optional[int]
    candidate_name: str
    total_votes: int


class SessionOverview(SessionRead):
    total_votes: int
    remaining_expected_votes: int
