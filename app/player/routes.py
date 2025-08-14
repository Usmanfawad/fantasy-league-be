from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.db_models import Player, PlayerStat
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
    stmt = select(Player)
    if active_only:
        stmt = stmt.where(Player.is_active == True)  # noqa: E712
    if team_id is not None:
        stmt = stmt.where(Player.team_id == team_id)
    if position_id is not None:
        stmt = stmt.where(Player.position_id == position_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Player.player_fullname.ilike(like))
            | (Player.player_firstname.ilike(like))
            | (Player.player_lastname.ilike(like))
        )

    total = len(session.exec(stmt).all())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = session.exec(stmt).all()
    data = [
        {
            "player_id": p.player_id,
            "name": p.player_fullname,
            "team_id": p.team_id,
            "position_id": p.position_id,
            "price": str(p.current_price),
            "active": p.is_active,
        }
        for p in items
    ]
    return ResponseSchema.pagination_response(data, total=total, page=page, page_size=page_size)


@player_router.get("/{player_id}")
def get_player(player_id: int, session: Session = Depends(get_session)):
    p = session.get(Player, player_id)
    if not p:
        return ResponseSchema.not_found("Player not found")
    data: dict[str, Any] = {
        "player_id": p.player_id,
        "name": p.player_fullname,
        "team_id": p.team_id,
        "position_id": p.position_id,
        "initial_price": str(p.initial_price),
        "current_price": str(p.current_price),
        "active": p.is_active,
    }
    return ResponseSchema.success(data=data)


@player_router.get("/{player_id}/stats")
def get_player_stats(
    player_id: int,
    session: Session = Depends(get_session),
):
    p = session.get(Player, player_id)
    if not p:
        return ResponseSchema.not_found("Player not found")
    stats = session.exec(
        select(PlayerStat).where(PlayerStat.player_id == player_id)
    ).all()
    data = [
        {
            "gw_id": s.gw_id,
            "points": s.total_points,
            "goals": s.goals_scored,
            "assists": s.assists,
            "yellow": s.yellow_cards,
            "red": s.red_cards,
            "minutes": s.minutes_played,
        }
        for s in stats
    ]
    return ResponseSchema.success(data=data)

@player_router.get("/stats")
def players_stats(
    gw_id: int | None = Query(None),
    team_id: int | None = Query(None),
    position_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    stmt = select(PlayerStat, Player).join(Player, Player.player_id == PlayerStat.player_id)
    if gw_id is not None:
        stmt = stmt.where(PlayerStat.gw_id == gw_id)
    if team_id is not None:
        stmt = stmt.where(Player.team_id == team_id)
    if position_id is not None:
        stmt = stmt.where(Player.position_id == position_id)

    rows = session.exec(stmt).all()
    total = len(rows)
    rows = rows[(page - 1) * page_size : (page - 1) * page_size + page_size]
    data = [
        {
            "player_id": p.player_id,
            "name": p.player_fullname,
            "gw_id": ps.gw_id,
            "points": ps.total_points,
            "goals": ps.goals_scored,
            "assists": ps.assists,
            "yellow": ps.yellow_cards,
            "red": ps.red_cards,
            "minutes": ps.minutes_played,
        }
        for (ps, p) in rows
    ]
    return ResponseSchema.pagination_response(data, total=total, page=page, page_size=page_size)


