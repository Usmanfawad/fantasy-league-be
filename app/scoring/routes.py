from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db_models import PlayerStat
from app.utils.db import get_session
from app.utils.responses import ResponseSchema


scoring_router = APIRouter(tags=["Scoring"])


@scoring_router.get("/scoring/{gameweek}")
def points_for_gameweek(gameweek: int, session: Session = Depends(get_session)):
    rows = session.exec(select(PlayerStat).where(PlayerStat.gw_id == gameweek)).all()
    data = [
        {
            "player_id": r.player_id,
            "gw_id": r.gw_id,
            "points": r.total_points,
        }
        for r in rows
    ]
    return ResponseSchema.success(data=data)


@scoring_router.get("/scoring/live")
def live_scoring_placeholder():
    return ResponseSchema.not_implemented(
        message="Live scoring integration pending external feed discussion"
    )


