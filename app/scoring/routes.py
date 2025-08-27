from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.scoring.service import ScoringService
from app.utils.db import get_session
from app.utils.responses import ResponseSchema

scoring_router = APIRouter(tags=["Scoring"])


class PlayerStatsUpdate(BaseModel):
    goals: int | None = None
    assists: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    clean_sheets: int | None = None
    bonus_points: int | None = None
    minutes_played: int | None = None
    started: bool | None = None


@scoring_router.get("/scoring/{gameweek}")
def points_for_gameweek(gameweek: str, session: Session = Depends(get_session)):
    data = ScoringService(session).points_for_gameweek(gameweek)
    return ResponseSchema.success(data=data)


# @scoring_router.post("/scoring/{gameweek}/recalculate")
# def recalculate_gameweek_points(gameweek: str, session: Session = Depends(get_session)):
#     """Recalculate points for all players in a gameweek using the scoring rules."""
#     try:
#         gw_id = int(gameweek)
#         ScoringService(session).recalculate_gameweek_points(gw_id)
#         return ResponseSchema.success(message=f"Points recalculated for gameweek {gameweek}")
#     except ValueError:
#         return ResponseSchema.bad_request("Invalid gameweek ID")


@scoring_router.put("/scoring/players/{player_id}/gameweek/{gameweek}")
def update_player_stats(
    player_id: int,
    gameweek: str,
    stats: PlayerStatsUpdate,
    session: Session = Depends(get_session)
):
    """Update player stats and automatically recalculate points."""
    try:
        gw_id = int(gameweek)
        ScoringService(session).update_player_stats_and_points(
            player_id=player_id,
            gw_id=gw_id,
            goals=stats.goals,
            assists=stats.assists,
            yellow_cards=stats.yellow_cards,
            red_cards=stats.red_cards,
            clean_sheets=stats.clean_sheets,
            bonus_points=stats.bonus_points,
            minutes_played=stats.minutes_played,
            started=stats.started
        )
        return ResponseSchema.success(message=f"Player {player_id} stats updated and points recalculated")
    except ValueError:
        return ResponseSchema.bad_request("Invalid gameweek ID")


@scoring_router.get("/scoring/rules")
def get_scoring_rules(session: Session = Depends(get_session)):
    """Get current scoring rules."""
    rules = ScoringService(session).get_scoring_rules()
    return ResponseSchema.success(data=rules)


@scoring_router.get("/scoring/live")
def live_scoring_placeholder():
    return ResponseSchema.success(
        message="Live scoring integration pending external feed discussion"
    )





