from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.fixtures.service import FixturesService
from app.utils.db import get_session
from app.utils.responses import ResponseSchema

fixtures_router = APIRouter(tags=["Fixtures"])


@fixtures_router.get("/fixtures")
def list_upcoming_fixtures(session: Session = Depends(get_session)):
    data = FixturesService(session).list_fixtures()
    return ResponseSchema.success(data=data)


@fixtures_router.get("/fixtures/{gameweek_id}")
def fixtures_for_gw(gameweek_id: str, session: Session = Depends(get_session)):
    data = FixturesService(session).fixtures_for_gw(gameweek_id)
    return ResponseSchema.success(data=data)


@fixtures_router.get("/results/{gameweek_id}")
def results_for_gw(gameweek_id: str, session: Session = Depends(get_session)):
    data = FixturesService(session).results_for_gw(gameweek_id)
    return ResponseSchema.success(data=data)


@fixtures_router.post("/gameweeks", status_code=status.HTTP_201_CREATED)
def create_gameweek(
    gw_number: int,
    start_date: str | None = None,
    end_date: str | None = None,
    session: Session = Depends(get_session),
):
    """Create a new gameweek. Optionally start/end dates; default status=open."""
    from datetime import datetime

    from app.db_models import Gameweek
    # Prevent duplicate numbers
    existing = session.exec(select(Gameweek).where(Gameweek.gw_number == gw_number)).first()
    if existing:
        return ResponseSchema.bad_request("Gameweek number already exists")

    gw = Gameweek(
        gw_id=None,
        gw_number=gw_number,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        status="open",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(gw)
    session.commit()
    session.refresh(gw)
    return ResponseSchema.success(data={"gw_id": str(gw.gw_id), "gw_number": gw.gw_number})


@fixtures_router.put("/gameweeks/{gw_id}/activate")
def activate_gameweek(gw_id: str, session: Session = Depends(get_session)):
    from app.db_models import Gameweek

    # Complete any currently active gameweek first and recalculate manager totals
    rows = session.exec(select(Gameweek)).all()
    prev_active: Gameweek | None = None
    for g in rows:
        if g.status == "active" and str(g.gw_id) != gw_id:
            g.status = "completed"
            prev_active = g
            session.add(g)
    from uuid import UUID
    gw = session.get(Gameweek, UUID(gw_id))
    if not gw:
        return ResponseSchema.not_found("Gameweek not found")
    gw.status = "active"
    session.add(gw)
    session.commit()

    # After committing previous GW completion, apply penalties by recalculating totals
    if prev_active is not None:
        from app.scoring.service import ScoringService
        scoring = ScoringService(session)
        scoring.recalculate_all_manager_points(prev_active.gw_id)

    return ResponseSchema.success(message="Gameweek activated", data={"gw_id": str(gw.gw_id)})


