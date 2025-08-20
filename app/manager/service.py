from __future__ import annotations

from collections import defaultdict
from typing import Any

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


class ManagerService:
    def __init__(self, session: Session):
        self.session = session

    def get_active_gameweek(self) -> Gameweek | None:
        return self.session.exec(select(Gameweek).where(Gameweek.status == "active")).first()

    def validate_and_save_squad(self, manager_id: int, players_payload: list[dict[str, Any]], gw_id: int | None) -> str:
        gw = self.session.get(Gameweek, gw_id) if gw_id is not None else None
        if gw is None:
            gw = self.get_active_gameweek()
        if gw is None:
            return "No active gameweek"

        if len(players_payload) != 15:
            return "Squad must contain exactly 15 players (11 starters and 4 substitutes)"

        player_ids = [p["player_id"] for p in players_payload]
        rows = self.session.exec(
            select(Player, Team).where(Player.player_id.in_(player_ids)).join(Team, Team.team_id == Player.team_id)
        ).all()
        if len(rows) != 15:
            return "Invalid player IDs or duplicates provided"

        team_counts: dict[int, int] = defaultdict(int)
        pos_counts: dict[int, int] = defaultdict(int)
        for player, team in rows:
            team_counts[team.team_id] += 1
            pos_counts[player.position_id] += 1
            if team_counts[team.team_id] > 3:
                return "No more than 3 players from the same team"

        required = {1: 2, 2: 5, 3: 5, 4: 3}
        if any(pos_counts.get(pid, 0) != count for pid, count in required.items()):
            return "Position quotas not satisfied"

        starters = sum(1 for p in players_payload if p.get("is_starter", True))
        if starters != 11:
            return "There must be exactly 11 starters"
        captains = sum(1 for p in players_payload if p.get("is_captain"))
        vice = sum(1 for p in players_payload if p.get("is_vice_captain"))
        if captains not in (0, 1) or vice not in (0, 1):
            return "Captain and vice-captain are optional but must be at most one each"

        # Replace existing squad
        self.session.exec(
            delete(ManagersSquad).where(
                (ManagersSquad.manager_id == manager_id) & (ManagersSquad.gw_id == gw.gw_id)
            )
        )
        for p in players_payload:
            self.session.add(
                ManagersSquad(
                    manager_id=manager_id,
                    player_id=p["player_id"],
                    gw_id=gw.gw_id,
                    is_captain=bool(p.get("is_captain", False)),
                    is_vice_captain=bool(p.get("is_vice_captain", False)),
                    is_starter=bool(p.get("is_starter", True)),
                )
            )
        self.session.commit()
        return "OK"

    def get_squad(self, manager_id: int) -> tuple[str | None, list[dict[str, Any]]]:
        gw = self.get_active_gameweek()
        if gw is None:
            return "No active gameweek", []
        rows = self.session.exec(
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
        return None, data

    def overview(self, manager_id: int) -> tuple[str | None, dict[str, Any]]:
        gw = self.get_active_gameweek()
        if gw is None:
            return "No active gameweek", {}
        rows = self.session.exec(
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
        return None, {"total_points": total_points, "players": details}

    def leaderboard(self, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
        gw = self.get_active_gameweek()
        if gw is None:
            return [], 0
        rows = self.session.exec(
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
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], total

    def make_transfer(self, manager_id: int, player_out_id: int, player_in_id: int, gw_id: int | None) -> str:
        gw = self.session.get(Gameweek, gw_id) if gw_id is not None else None
        if gw is None:
            gw = self.get_active_gameweek()
        if gw is None:
            return "No active gameweek"

        current_ids = [
            t[0]
            for t in self.session.exec(
                select(ManagersSquad.player_id)
                .where(ManagersSquad.manager_id == manager_id)
                .where(ManagersSquad.gw_id == gw.gw_id)
            ).all()
        ]
        if player_out_id not in current_ids:
            return "Player out is not in current squad"
        if player_in_id in current_ids:
            return "Player in is already in current squad"

        manager = self.session.get(Manager, manager_id)
        if not manager:
            return "Manager not found"
        penalty = 4
        if manager.wallet < penalty:
            return "Insufficient wallet for penalty"
        manager.wallet -= penalty
        self.session.add(manager)

        self.session.add(
            Transfer(
                transfer_id=None,
                manager_id=manager_id,
                player_in_id=player_in_id,
                player_out_id=player_out_id,
                gw_id=gw.gw_id,
            )
        )
        self.session.exec(
            update(ManagersSquad)
            .where(
                (ManagersSquad.manager_id == manager_id)
                & (ManagersSquad.gw_id == gw.gw_id)
                & (ManagersSquad.player_id == player_out_id)
            )
            .values(player_id=player_in_id)
        )
        self.session.commit()
        return "OK"

    def substitute(self, manager_id: int, player_out_id: int, player_in_id: int) -> str:
        gw = self.get_active_gameweek()
        if gw is None:
            return "No active gameweek"
        out_row = self.session.exec(
            select(ManagersSquad).where(
                (ManagersSquad.manager_id == manager_id)
                & (ManagersSquad.gw_id == gw.gw_id)
                & (ManagersSquad.player_id == player_out_id)
            )
        ).first()
        in_row = self.session.exec(
            select(ManagersSquad).where(
                (ManagersSquad.manager_id == manager_id)
                & (ManagersSquad.gw_id == gw.gw_id)
                & (ManagersSquad.player_id == player_in_id)
            )
        ).first()
        if not out_row or not in_row:
            return "Both players must be in the squad"
        out_row.is_starter, in_row.is_starter = in_row.is_starter, out_row.is_starter
        self.session.add(out_row)
        self.session.add(in_row)
        self.session.commit()
        return "OK"

    def update_transfer(self, manager_id: int, transfer_id: int, player_out_id: int, player_in_id: int) -> str:
        gw = self.get_active_gameweek()
        if gw is None:
            return "No active gameweek"
        tr = self.session.get(Transfer, transfer_id)
        if not tr or tr.manager_id != manager_id:
            return "Transfer not found"
        tr.player_out_id = player_out_id
        tr.player_in_id = player_in_id
        self.session.add(tr)
        self.session.commit()
        return "OK"



