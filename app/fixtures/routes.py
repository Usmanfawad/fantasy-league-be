from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db_models import Fixture, Gameweek
from app.utils.db import get_session
from app.utils.responses import ResponseSchema


fixtures_router = APIRouter(tags=["Fixtures"])


@fixtures_router.get("/fixtures")
def list_upcoming_fixtures(session: Session = Depends(get_session)):
    rows = session.exec(
        select(Fixture, Gameweek).join(Gameweek, Gameweek.gw_id == Fixture.gw_id)
    ).all()
    data = [
        {
            "fixture_id": f.fixture_id,
            "gw_id": f.gw_id,
            "home_team_id": f.home_team_id,
            "away_team_id": f.away_team_id,
            "date": f.date.isoformat(),
            "home_team_score": f.home_team_score,
            "away_team_score": f.away_team_score,
            "gw_status": gw.status,
        }
        for (f, gw) in rows
    ]
    return ResponseSchema.success(data=data)


@fixtures_router.get("/fixtures/{gameweek_id}")
def fixtures_for_gw(gameweek_id: int, session: Session = Depends(get_session)):
    rows = session.exec(select(Fixture).where(Fixture.gw_id == gameweek_id)).all()
    data = [
        {
            "fixture_id": f.fixture_id,
            "gw_id": f.gw_id,
            "home_team_id": f.home_team_id,
            "away_team_id": f.away_team_id,
            "date": f.date.isoformat(),
            "home_team_score": f.home_team_score,
            "away_team_score": f.away_team_score,
        }
        for f in rows
    ]
    return ResponseSchema.success(data=data)


@fixtures_router.get("/results/{gameweek_id}")
def results_for_gw(gameweek_id: int, session: Session = Depends(get_session)):
    rows = session.exec(select(Fixture).where(Fixture.gw_id == gameweek_id)).all()
    data = [
        {
            "fixture_id": f.fixture_id,
            "home_team_score": f.home_team_score,
            "away_team_score": f.away_team_score,
        }
        for f in rows
    ]
    return ResponseSchema.success(data=data)


