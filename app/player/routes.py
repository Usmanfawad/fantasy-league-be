from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.player.service import PlayerService
from app.utils.db import get_session
from app.utils.responses import ResponseSchema

player_router = APIRouter(prefix="/players", tags=["Players"])


@player_router.get("")
def list_players(
    q: str | None = Query(None),
    team_id: int | None = Query(None),
    position_id: int | None = Query(None),
    active_only: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    svc = PlayerService(session)
    data, total = svc.list_players(q, team_id, position_id, active_only, page, page_size)
    return ResponseSchema.pagination_response(data, total=total, page=page, page_size=page_size)


@player_router.get("/stats")
def players_stats(
    gw_id: int | None = Query(None),
    team_id: int | None = Query(None),
    position_id: int | None = Query(None),
    sort: str | None = Query("cumulative_points"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    svc = PlayerService(session)
    data, total = svc.players_stats(gw_id, team_id, position_id, sort, page, page_size)
    return ResponseSchema.pagination_response(data, total=total, page=page, page_size=page_size)


@player_router.get("/{player_id}")
def get_player(player_id: int, session: Session = Depends(get_session)):
    svc = PlayerService(session)
    data = svc.get_player(player_id)
    if not data:
        return ResponseSchema.not_found("Player not found")
    return ResponseSchema.success(data=data)


@player_router.get("/{player_id}/stats")
def get_player_stats(
    player_id: int,
    session: Session = Depends(get_session),
):
    svc = PlayerService(session)
    data = svc.get_player_stats(player_id)
    if data is None:
        return ResponseSchema.not_found("Player not found")
    return ResponseSchema.success(data=data)

 


# Teams endpoints moved to a dedicated router


