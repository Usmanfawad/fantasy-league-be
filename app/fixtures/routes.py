from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.fixtures.service import FixturesService
from app.utils.db import get_session
from app.utils.responses import ResponseSchema

fixtures_router = APIRouter(prefix="/fixtures", tags=["Fixtures"])
gameweeks_router = APIRouter(tags=["Gameweeks"])


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


@gameweeks_router.post("", status_code=status.HTTP_201_CREATED)
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


@gameweeks_router.post("/complete-current")
def complete_current_gameweek(session: Session = Depends(get_session)):
    """
    Complete current gameweek and prepare next gameweek.
    
    Flow:
    1. Find current 'open' gameweek
    2. Mark it as completed
    3. Copy all manager squads to next gameweek
    4. Open next gameweek for transfers
    """
    from app.db_models import Gameweek
    from app.fixtures.service import FixturesService

    # Find current open gameweek
    current_gw = session.exec(
        select(Gameweek)
        .where(Gameweek.status == "open")
        .order_by(Gameweek.gw_number)
    ).first()
    
    if not current_gw:
        return ResponseSchema.bad_request("No open gameweek found to complete")

    # Find next gameweek
    next_gw = session.exec(
        select(Gameweek)
        .where(
            (Gameweek.gw_number > current_gw.gw_number) &
            (Gameweek.status == "upcoming")
        )
        .order_by(Gameweek.gw_number)
    ).first()
    
    if not next_gw:
        return ResponseSchema.bad_request("No upcoming gameweek found to open")

    # Mark current as completed
    current_gw.status = "completed"
    current_gw.updated_at = datetime.utcnow()
    session.add(current_gw)
    
    # Open next gameweek
    next_gw.status = "open"
    next_gw.updated_at = datetime.utcnow()
    session.add(next_gw)
    
    # Commit changes
    session.commit()
    
    # Copy squads to next gameweek
    svc = FixturesService(session)
    svc.copy_squads_to_next_gameweek(current_gw.gw_id)
    
    # Recalculate points with penalties
    from app.scoring.service import ScoringService
    scoring = ScoringService(session)
    scoring.recalculate_all_manager_points(current_gw.gw_id)
    
    return ResponseSchema.success(
        message="Gameweek transition completed",
        data={
            "completed_gw": {
                "id": str(current_gw.gw_id),
                "number": current_gw.gw_number
            },
            "opened_gw": {
                "id": str(next_gw.gw_id),
                "number": next_gw.gw_number
            }
        }
    )


@gameweeks_router.post("/open-next")
def open_next_gameweek(session: Session = Depends(get_session)):
    """Open the transfer window for the next gameweek (oldest upcoming)."""
    from app.fixtures.service import FixturesService
    
    svc = FixturesService(session)
    success, message, opened_gw = svc.open_transfer_window()
    
    if not success:
        return ResponseSchema.bad_request(message)
        
    return ResponseSchema.success(
        message=message,
        data={
            "gw_id": str(opened_gw.gw_id),
            "gw_number": opened_gw.gw_number,
            "status": opened_gw.status
        }
    )


