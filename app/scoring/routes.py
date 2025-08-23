from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.scoring.service import ScoringService
from app.utils.db import get_session
from app.utils.responses import ResponseSchema

scoring_router = APIRouter(tags=["Scoring"])


@scoring_router.get("/scoring/{gameweek}")
def points_for_gameweek(gameweek: str, session: Session = Depends(get_session)):
    data = ScoringService(session).points_for_gameweek(gameweek)
    return ResponseSchema.success(data=data)


@scoring_router.get("/scoring/live")
def live_scoring_placeholder():
    return ResponseSchema.not_implemented(
        message="Live scoring integration pending external feed discussion"
    )


