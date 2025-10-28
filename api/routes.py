from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import func
from sqlmodel import Session, select

from database import get_session
from models import Candidate, PollWorker, SessionStatus, Vote, VotePermit, VotingSession
from schemas import (
    CandidateCreate,
    CandidateRead,
    PermitRead,
    PollWorkerCreate,
    PollWorkerRead,
    SessionCreate,
    SessionOverview,
    SessionRead,
    VoteRead,
    VoteRequest,
    VoteSummary,
)
from services.authorization import authorization_manager

router = APIRouter()


def _ensure_session_exists(session: Session, session_id: int) -> VotingSession:
    voting_session = session.get(VotingSession, session_id)
    if voting_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return voting_session


@router.post("/sessions", response_model=SessionRead, status_code=201)
def create_session(data: SessionCreate, session: Session = Depends(get_session)) -> VotingSession:
    existing = session.exec(select(VotingSession).where(VotingSession.code == data.code)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Session code already exists")

    new_session = VotingSession(code=data.code, expected_votes=data.expected_votes)
    session.add(new_session)
    session.commit()
    session.refresh(new_session)
    return new_session


@router.get("/sessions", response_model=List[SessionOverview])
def list_sessions(session: Session = Depends(get_session)) -> List[SessionOverview]:
    sessions = session.exec(select(VotingSession)).all()
    summaries: list[SessionOverview] = []
    for item in sessions:
        total_votes = session.exec(
            select(func.count(Vote.id)).where(Vote.session_id == item.id)
        ).one()
        total_votes = int(total_votes or 0)
        remaining = max(item.expected_votes - total_votes, 0)
        summaries.append(
            SessionOverview(
                id=item.id,
                code=item.code,
                expected_votes=item.expected_votes,
                status=item.status,
                start_time=item.start_time,
                end_time=item.end_time,
                total_votes=total_votes,
                remaining_expected_votes=remaining,
            )
        )
    return summaries


@router.post("/sessions/{session_id}/start", response_model=SessionRead)
def start_session(session_id: int, session: Session = Depends(get_session)) -> VotingSession:
    voting_session = _ensure_session_exists(session, session_id)
    if voting_session.status == SessionStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Session already closed")
    if voting_session.status == SessionStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Session already in progress")

    voting_session.status = SessionStatus.IN_PROGRESS
    voting_session.start_time = datetime.utcnow()
    session.add(voting_session)
    session.commit()
    session.refresh(voting_session)
    return voting_session


@router.post("/sessions/{session_id}/close", response_model=SessionRead)
def close_session(session_id: int, session: Session = Depends(get_session)) -> VotingSession:
    voting_session = _ensure_session_exists(session, session_id)
    if voting_session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Session must be in progress to be closed")

    voting_session.status = SessionStatus.CLOSED
    voting_session.end_time = datetime.utcnow()
    session.add(voting_session)
    session.commit()
    session.refresh(voting_session)
    return voting_session


@router.post("/sessions/{session_id}/candidates", response_model=CandidateRead, status_code=201)
def create_candidate(
    session_id: int, data: CandidateCreate, session: Session = Depends(get_session)
) -> Candidate:
    voting_session = _ensure_session_exists(session, session_id)

    candidate = Candidate(
        name=data.name,
        registration=data.registration,
        commission_number=data.commission_number,
        session_id=voting_session.id,
    )
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    return candidate


@router.get("/sessions/{session_id}/candidates", response_model=List[CandidateRead])
def list_candidates(session_id: int, session: Session = Depends(get_session)) -> List[Candidate]:
    _ensure_session_exists(session, session_id)
    candidates = session.exec(select(Candidate).where(Candidate.session_id == session_id)).all()
    return candidates


@router.post("/sessions/{session_id}/poll_workers", response_model=PollWorkerRead, status_code=201)
def add_poll_worker(
    session_id: int, data: PollWorkerCreate, session: Session = Depends(get_session)
) -> PollWorker:
    voting_session = _ensure_session_exists(session, session_id)

    worker = PollWorker(name=data.name, registration=data.registration, session_id=voting_session.id)
    session.add(worker)
    session.commit()
    session.refresh(worker)
    return worker


@router.get("/sessions/{session_id}/poll_workers", response_model=List[PollWorkerRead])
def list_poll_workers(session_id: int, session: Session = Depends(get_session)) -> List[PollWorker]:
    _ensure_session_exists(session, session_id)
    workers = session.exec(select(PollWorker).where(PollWorker.session_id == session_id)).all()
    return workers


@router.post("/sessions/{session_id}/permits", response_model=PermitRead, status_code=201)
async def create_vote_permit(
    session_id: int, session: Session = Depends(get_session)
) -> PermitRead:
    voting_session = _ensure_session_exists(session, session_id)
    if voting_session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Session is not open for voting")

    token = authorization_manager.generate_token()
    permit = VotePermit(token=token, session_id=session_id)
    session.add(permit)
    session.commit()
    session.refresh(permit)

    await authorization_manager.notify_new_permit(permit)

    return PermitRead(token=permit.token, issued_at=permit.issued_at)


@router.post("/sessions/{session_id}/votes", response_model=VoteRead, status_code=201)
def register_vote(
    session_id: int, data: VoteRequest, session: Session = Depends(get_session)
) -> Vote:
    voting_session = _ensure_session_exists(session, session_id)
    if voting_session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Session is not accepting votes")

    candidate = session.get(Candidate, data.candidate_id)
    if candidate is None or candidate.session_id != session_id:
        raise HTTPException(status_code=400, detail="Invalid candidate for this session")

    permit = session.exec(select(VotePermit).where(VotePermit.token == data.permit_token)).first()
    if permit is None or permit.session_id != session_id:
        raise HTTPException(status_code=400, detail="Invalid authorization token")
    if permit.used:
        raise HTTPException(status_code=400, detail="Authorization token already used")

    vote = Vote(session_id=session_id, candidate_id=candidate.id, permit_id=permit.id)
    permit.used = True
    permit.used_at = datetime.utcnow()

    session.add(vote)
    session.add(permit)
    session.commit()
    session.refresh(vote)

    return vote


@router.get("/sessions/{session_id}/results", response_model=List[VoteSummary])
def session_results(session_id: int, session: Session = Depends(get_session)) -> List[VoteSummary]:
    _ensure_session_exists(session, session_id)
    candidates = session.exec(select(Candidate).where(Candidate.session_id == session_id)).all()
    summaries: list[VoteSummary] = []
    for candidate in candidates:
        vote_count = session.exec(
            select(func.count(Vote.id)).where(Vote.candidate_id == candidate.id)
        ).one()
        vote_count = int(vote_count or 0)
        summaries.append(
            VoteSummary(
                candidate_id=candidate.id,
                candidate_name=candidate.name,
                total_votes=vote_count,
            )
        )
    return summaries


@router.websocket("/ws/sessions/{session_id}/cabine")
async def cabin_websocket(session_id: int, websocket: WebSocket) -> None:
    await websocket.accept()
    await authorization_manager.register_cabin(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await authorization_manager.unregister_cabin(session_id, websocket)


@router.websocket("/ws/sessions/{session_id}/mesario")
async def mesario_websocket(session_id: int, websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_json()
            action = message.get("action")
            if action == "authorize":
                from ..database import session_scope

                with session_scope() as db_session:
                    voting_session = _ensure_session_exists(db_session, session_id)
                    if voting_session.status != SessionStatus.IN_PROGRESS:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "detail": "Session is not open for voting",
                            }
                        )
                        continue
                    token = authorization_manager.generate_token()
                    permit = VotePermit(token=token, session_id=session_id)
                    db_session.add(permit)
                    db_session.commit()
                    db_session.refresh(permit)
                await authorization_manager.notify_new_permit(permit)
                await websocket.send_json(
                    {
                        "type": "authorized",
                        "token": permit.token,
                        "issued_at": permit.issued_at.isoformat(),
                    }
                )
            else:
                await websocket.send_json({"type": "error", "detail": "Unknown action"})
    except WebSocketDisconnect:
        return
