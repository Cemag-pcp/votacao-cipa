from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import timezone, timedelta
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore
from sqlalchemy import func
from sqlmodel import Session, select

from database import get_session
from models import Candidate, PollWorker, SessionStatus, Vote, VotingSession

router = APIRouter(tags=["Web"])

templates = Jinja2Templates(directory="templates")
templates.env.globals["now"] = datetime.utcnow

# Register a Jinja filter to format UTC datetimes in America/Sao_Paulo
try:
    LOCAL_TZ = ZoneInfo("America/Sao_Paulo") if ZoneInfo else None  # type: ignore
except Exception:
    LOCAL_TZ = None
if LOCAL_TZ is None:
    # Fallback: fixed offset -03:00 (Brazil currently sem DST)
    LOCAL_TZ = timezone(timedelta(hours=-3))

def _to_local(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ)


def fmt_dt(dt: datetime | None, fmt: str = "%d/%m/%Y %H:%M") -> str:
    try:
        local_dt = _to_local(dt)
        return local_dt.strftime(fmt) if local_dt else "-"
    except Exception:
        return "-"


templates.env.filters["fmt_dt"] = fmt_dt


def _session_overview(db_session: Session, voting_session: VotingSession) -> Dict[str, Any]:
    total_votes = db_session.exec(
        select(func.count(Vote.id)).where(Vote.session_id == voting_session.id)
    ).one()
    total_votes = int(total_votes or 0)
    remaining_votes = max(voting_session.expected_votes - total_votes, 0)
    return {
        "id": voting_session.id,
        "code": voting_session.code,
        "status": voting_session.status,
        "expected_votes": voting_session.expected_votes,
        "start_time": _to_local(voting_session.start_time),
        "end_time": _to_local(voting_session.end_time),
        "total_votes": total_votes,
        "remaining_votes": remaining_votes,
    }


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request, db_session: Session = Depends(get_session)
) -> HTMLResponse:
    sessions = db_session.exec(select(VotingSession).order_by(VotingSession.code)).all()
    overviews = [_session_overview(db_session, item) for item in sessions]
    context = {
        "request": request,
        "sessions": overviews,
    }
    return templates.TemplateResponse("index.html", context)


@router.get("/sessions", response_class=HTMLResponse)
def list_sessions(
    request: Request, db_session: Session = Depends(get_session)
) -> HTMLResponse:
    sessions = db_session.exec(select(VotingSession).order_by(VotingSession.code)).all()
    overviews = [_session_overview(db_session, item) for item in sessions]
    context = {
        "request": request,
        "sessions": overviews,
    }
    return templates.TemplateResponse("sessions/list.html", context)


@router.get("/sessions/new", response_class=HTMLResponse)
def new_session(request: Request) -> HTMLResponse:
    context = {"request": request}
    return templates.TemplateResponse("sessions/create.html", context)


@router.get("/sessions/{session_id}", response_class=HTMLResponse)
def session_detail(
    session_id: int, request: Request, db_session: Session = Depends(get_session)
) -> HTMLResponse:
    voting_session = db_session.get(VotingSession, session_id)
    if voting_session is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    session_data = _session_overview(db_session, voting_session)

    candidates = db_session.exec(
        select(Candidate).where(Candidate.session_id == voting_session.id)
    ).all()
    workers = db_session.exec(
        select(PollWorker).where(PollWorker.session_id == voting_session.id)
    ).all()

    candidate_votes: List[Dict[str, Any]] = []
    for candidate in candidates:
        vote_count = db_session.exec(
            select(func.count(Vote.id)).where(Vote.candidate_id == candidate.id)
        ).one()
        vote_count = int(vote_count or 0)
        candidate_votes.append(
            {
                "id": candidate.id,
                "name": candidate.name,
                "registration": candidate.registration,
                "commission_number": candidate.commission_number,
                "photo_url": candidate.photo_url,
                "votes": vote_count,
            }
        )

    # Ordena os candidatos por número de votos (maior para menor) apenas se a sessão estiver encerrada
    if voting_session.status == SessionStatus.CLOSED:
        candidate_votes.sort(key=lambda c: c["votes"], reverse=True)

    null_votes = db_session.exec(
        select(func.count(Vote.id)).where((Vote.session_id == voting_session.id) & (Vote.candidate_id == None))
    ).one()
    null_votes = int(null_votes or 0)

    context = {
        "request": request,
        "session": session_data,
        "session_status": SessionStatus,
        "candidates": candidate_votes,
        "null_votes": null_votes,
        "poll_workers": workers,
    }
    return templates.TemplateResponse("sessions/detail.html", context)


@router.get("/sessions/{session_id}/mesario", response_class=HTMLResponse)
def session_mesario(
    session_id: int, request: Request, db_session: Session = Depends(get_session)
) -> HTMLResponse:
    voting_session = db_session.get(VotingSession, session_id)
    if voting_session is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    context = {
        "request": request,
        "session": _session_overview(db_session, voting_session),
    }
    return templates.TemplateResponse("sessions/mesario.html", context)


@router.get("/sessions/{session_id}/cabine", response_class=HTMLResponse)
def session_cabin(
    session_id: int, request: Request, db_session: Session = Depends(get_session)
) -> HTMLResponse:
    voting_session = db_session.get(VotingSession, session_id)
    if voting_session is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    candidates = db_session.exec(
        select(Candidate).where(Candidate.session_id == voting_session.id)
    ).all()

    context = {
        "request": request,
        "session": _session_overview(db_session, voting_session),
        "candidates": candidates,
        # Ativa o modo cabine/urna (sem navegação/saída)
        "kiosk_mode": True,
    }
    return templates.TemplateResponse("sessions/cabin.html", context)
