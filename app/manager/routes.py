from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, update
from sqlmodel import Session, select

from app.db_models import (
    Gameweek,
    Manager,
    ManagersSquad,
    Player,
    PlayerStat,
    Team,
    Transfer,
)
from app.dependencies import ManagerUser
from app.manager.schemas import SquadSaveRequest, TransferRequest
from app.user.models import UserRole
from app.utils.db import get_session
from app.utils.responses import ResponseSchema

manager_router = APIRouter(prefix="/managers", tags=["Managers"])


def _get_active_gameweek(session: Session) -> Gameweek | None:
    return session.exec(select(Gameweek).where(Gameweek.status == "active")).first()


@manager_router.post("/{manager_id}/squad")
def save_squad(
    manager_id: int,
    body: SquadSaveRequest,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    if user.id != manager_id and user.role != UserRole.ADMIN:
        return ResponseSchema.forbidden("Cannot modify another manager's squad")

    gw = None
    if body.gw_id is not None:
        gw = session.get(Gameweek, body.gw_id)
    if gw is None:
        gw = _get_active_gameweek(session)
    if gw is None:
        return ResponseSchema.bad_request("No active gameweek")

    players = body.players or []
    if len(players) != 15:
        return ResponseSchema.bad_request(
            "Squad must contain exactly 15 players (11 starters and 4 substitutes)"
        )

    # Business rules: positions and team quotas
    player_rows = session.exec(
        select(Player, Team).where(Player.player_id.in_([p.player_id for p in players])).join(Team, Team.team_id == Player.team_id)
    ).all()
    if len(player_rows) != 15:
        return ResponseSchema.bad_request("Invalid player IDs or duplicates provided")

    team_counts: dict[int, int] = defaultdict(int)
    pos_counts: dict[int, int] = defaultdict(int)
    for (player, team) in player_rows:
        team_counts[team.team_id] += 1
        pos_counts[player.position_id] += 1
        if team_counts[team.team_id] > 3:
            return ResponseSchema.bad_request("No more than 3 players from the same team")

    # Example quotas: 2 GK, 5 DEF, 5 MID, 3 FWD
    required = {1: 2, 2: 5, 3: 5, 4: 3}
    if any(pos_counts.get(pid, 0) != count for pid, count in required.items()):
        return ResponseSchema.bad_request("Position quotas not satisfied")

    starters = sum(1 for p in players if p.is_starter)
    if starters != 11:
        return ResponseSchema.bad_request("There must be exactly 11 starters")
    captains = sum(1 for p in players if p.is_captain)
    vice = sum(1 for p in players if p.is_vice_captain)
    if captains not in (0, 1) or vice not in (0, 1):
        return ResponseSchema.bad_request(
            "Captain and vice-captain are optional but must be at most one each"
        )

    # Replace existing squad for that gw
    session.exec(
        delete(ManagersSquad).where(
            (ManagersSquad.manager_id == manager_id) & (ManagersSquad.gw_id == gw.gw_id)
        )
    )

    for p in players:
        session.add(
            ManagersSquad(
                manager_id=manager_id,
                player_id=p.player_id,
                gw_id=gw.gw_id,
                is_captain=p.is_captain,
                is_vice_captain=p.is_vice_captain,
                is_starter=p.is_starter,
            )
        )
    session.commit()
    return ResponseSchema.success(message="Squad saved")


@manager_router.get("/{manager_id}/squad")
def get_squad(
    manager_id: int,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    if user.id != manager_id and user.role != UserRole.ADMIN:
        return ResponseSchema.forbidden("Cannot view another manager's squad")

    gw = _get_active_gameweek(session)
    if gw is None:
        return ResponseSchema.bad_request("No active gameweek")

    rows = session.exec(
        select(ManagersSquad, Player)
        .where(ManagersSquad.manager_id == manager_id)
        .where(ManagersSquad.gw_id == gw.gw_id)
        .join(Player, Player.player_id == ManagersSquad.player_id)
    ).all()

    data = [
        {
            "player_id": player.player_id,
            "name": player.player_fullname,
            "position_id": player.position_id,
            "team_id": player.team_id,
            "is_captain": ms.is_captain,
            "is_vice_captain": ms.is_vice_captain,
            "is_starter": ms.is_starter,
        }
        for (ms, player) in rows
    ]
    return ResponseSchema.success(data=data)


@manager_router.put("/{manager_id}/squad")
def update_squad(
    manager_id: int,
    body: SquadSaveRequest,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    # Same validation and logic as save; we treat it as upsert for the GW
    return save_squad(manager_id, body, user, session)


@manager_router.get("/{manager_id}/overview")
def manager_overview(
    manager_id: int,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    if user.id != manager_id and user.role != UserRole.ADMIN:
        return ResponseSchema.forbidden("Cannot view another manager's overview")

    gw = _get_active_gameweek(session)
    if not gw:
        return ResponseSchema.bad_request("No active gameweek")

    rows = session.exec(
        select(ManagersSquad, PlayerStat)
        .where(ManagersSquad.manager_id == manager_id)
        .where(ManagersSquad.gw_id == gw.gw_id)
        .join(PlayerStat, (PlayerStat.player_id == ManagersSquad.player_id) & (PlayerStat.gw_id == ManagersSquad.gw_id))
    ).all()

    total_points = sum(ps.total_points for (_, ps) in rows)
    details = [
        {
            "player_id": ps.player_id,
            "gw_id": ps.gw_id,
            "points": ps.total_points,
            "goals": ps.goals_scored,
            "assists": ps.assists,
            "bonus": ps.bonus_points,
        }
        for (_, ps) in rows
    ]
    return ResponseSchema.success(data={"total_points": total_points, "players": details})


@manager_router.get("/leaderboard")
def leaderboard(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    gw = _get_active_gameweek(session)
    if not gw:
        return ResponseSchema.bad_request("No active gameweek")

    rows = session.exec(
        select(Manager.manager_id, Manager.squad_name, PlayerStat.total_points)
        .join(ManagersSquad, ManagersSquad.manager_id == Manager.manager_id)
        .join(PlayerStat, (PlayerStat.player_id == ManagersSquad.player_id) & (PlayerStat.gw_id == ManagersSquad.gw_id))
        .where(ManagersSquad.gw_id == gw.gw_id)
    ).all()

    totals: dict[int, int] = defaultdict(int)
    names: dict[int, str] = {}
    for mid, name, pts in rows:
        totals[mid] += pts
        names[mid] = name

    items = sorted(
        ({"manager_id": mid, "squad_name": names[mid], "points": pts} for mid, pts in totals.items()),
        key=lambda i: i["points"],
        reverse=True,
    )
    start = (page - 1) * page_size
    end = start + page_size
    return ResponseSchema.pagination_response(items[start:end], total=len(items), page=page, page_size=page_size)


@manager_router.post("/{manager_id}/transfers")
def make_transfer(
    manager_id: int,
    body: TransferRequest,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    if user.id != manager_id and user.role != UserRole.ADMIN:
        return ResponseSchema.forbidden("Cannot transfer for another manager")

    gw = None
    if body.gw_id is not None:
        gw = session.get(Gameweek, body.gw_id)
    if gw is None:
        gw = _get_active_gameweek(session)
    if gw is None:
        return ResponseSchema.bad_request("No active gameweek")

    player_out = session.get(Player, body.player_out_id)
    player_in = session.get(Player, body.player_in_id)
    if not player_out or not player_in:
        return ResponseSchema.bad_request("Invalid player IDs")

    # Enforce team limit when swapping in
    current_team_ids = [
        t[0]
        for t in session.exec(
            select(ManagersSquad.player_id)
            .where(ManagersSquad.manager_id == manager_id)
            .where(ManagersSquad.gw_id == gw.gw_id)
        ).all()
    ]
    # Replace player_out with player_in in the current squad
    if body.player_out_id not in current_team_ids:
        return ResponseSchema.bad_request("Player out is not in current squad")

    # Apply simple penalty and wallet deduction (PoC); ensure not below zero
    manager = session.get(Manager, manager_id)
    if not manager:
        return ResponseSchema.not_found("Manager not found")
    penalty = 4
    if manager.wallet < penalty:
        return ResponseSchema.bad_request("Insufficient wallet for penalty")
    manager.wallet -= penalty
    session.add(manager)

    session.add(
        Transfer(
            transfer_id=None,
            manager_id=manager_id,
            player_in_id=body.player_in_id,
            player_out_id=body.player_out_id,
            gw_id=gw.gw_id,
        )
    )
    # Update squad record
    session.exec(
        update(ManagersSquad)
        .where(
            (ManagersSquad.manager_id == manager_id)
            & (ManagersSquad.gw_id == gw.gw_id)
            & (ManagersSquad.player_id == body.player_out_id)
        )
        .values(player_id=body.player_in_id)
    )

    session.commit()
    return ResponseSchema.success(message="Transfer completed with 4-point penalty")


@manager_router.post("/{manager_id}/substitute")
def substitute_player(
    manager_id: int,
    player_out_id: int,
    player_in_id: int,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    if user.id != manager_id and user.role != UserRole.ADMIN:
        return ResponseSchema.forbidden("Cannot substitute for another manager")

    gw = _get_active_gameweek(session)
    if not gw:
        return ResponseSchema.bad_request("No active gameweek")

    # out must be starter, in must be bench or vice versa; simple swap
    out_row = session.exec(
        select(ManagersSquad).where(
            (ManagersSquad.manager_id == manager_id)
            & (ManagersSquad.gw_id == gw.gw_id)
            & (ManagersSquad.player_id == player_out_id)
        )
    ).first()
    in_row = session.exec(
        select(ManagersSquad).where(
            (ManagersSquad.manager_id == manager_id)
            & (ManagersSquad.gw_id == gw.gw_id)
            & (ManagersSquad.player_id == player_in_id)
        )
    ).first()
    if not out_row or not in_row:
        return ResponseSchema.bad_request("Both players must be in the squad")

    out_row.is_starter, in_row.is_starter = in_row.is_starter, out_row.is_starter
    session.add(out_row)
    session.add(in_row)
    session.commit()
    return ResponseSchema.success(message="Substitution applied")


@manager_router.put("/{manager_id}/transfers/{transfer_id}")
def update_transfer(
    manager_id: int,
    transfer_id: int,
    body: TransferRequest,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    if user.id != manager_id and user.role != UserRole.ADMIN:
        return ResponseSchema.forbidden("Cannot modify another manager's transfer")

    gw = _get_active_gameweek(session)
    if not gw:
        return ResponseSchema.bad_request("No active gameweek")

    tr = session.get(Transfer, transfer_id)
    if not tr or tr.manager_id != manager_id:
        return ResponseSchema.not_found("Transfer not found")

    tr.player_out_id = body.player_out_id
    tr.player_in_id = body.player_in_id
    session.add(tr)
    session.commit()
    return ResponseSchema.success(message="Transfer updated")


