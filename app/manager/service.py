from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, update
from sqlmodel import Session, select

from app.db_models import (
    Gameweek,
    Manager,
    ManagerGameweekState,
    ManagersSquad,
    Player,
    PlayerPrice,
    PlayerStat,
    Team,
    Transfer,
)


class ManagerService:
    def __init__(self, session: Session):
        self.session = session

    def _validate_position_quotas(self, player_ids: list[int]) -> tuple[bool, str]:
        """Validate position quotas for a list of player IDs.
        Returns (is_valid, error_message)"""
        rows = self.session.exec(
            select(Player, Team).where(Player.player_id.in_(player_ids)).join(
                Team, Team.team_id == Player.team_id
            )
        ).all()
        
        team_counts: dict[int, int] = defaultdict(int)
        pos_counts: dict[int, int] = defaultdict(int)
        for player, team in rows:
            team_counts[team.team_id] += 1
            pos_counts[player.position_id] += 1
            if team_counts[team.team_id] > 3:
                return False, "No more than 3 players from the same team"

        required = {1: 2, 2: 5, 3: 5, 4: 3}  # GK: 2, DEF: 5, MID: 5, FWD: 3
        if any(pos_counts.get(pid, 0) != count for pid, count in required.items()):
            return False, "Position quotas not satisfied"
            
        return True, "OK"

    def get_active_gameweek(self) -> Gameweek | None:
        # Latest active-like gameweek (treat legacy statuses as active)
        return self.session.exec(
            select(Gameweek)
            .where(Gameweek.status.in_(["active", "Ongoing", "open"]))
            .order_by(Gameweek.gw_number.desc())
            .limit(1)
        ).first()

    def validate_and_save_squad(self, manager_id: UUID, players_payload: list[dict[str, Any]], gw_id: int | None) -> str:
        gw = self.session.get(Gameweek, gw_id) if gw_id is not None else None
        if gw is None:
            gw = self.get_active_gameweek()
        if gw is None:
            return "No active gameweek"

        if len(players_payload) != 15:
            return "Squad must contain exactly 15 players (11 starters and 4 substitutes)"

        player_ids: list[int] = [p["player_id"] for p in players_payload]
        rows = self.session.exec(
            select(Player, Team).where(Player.player_id.in_(player_ids)).join(
                Team, Team.team_id == Player.team_id
            )
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
                (ManagersSquad.manager_id == manager_id) & 
                (ManagersSquad.gw_id == gw.gw_id)
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

    def get_squad(self, manager_id: UUID) -> tuple[str | None, list[dict[str, Any]]]:
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
                "player_id": str(player.player_id),
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

    def overview(self, manager_id: UUID) -> tuple[str | None, dict[str, Any]]:
        gw = self.get_active_gameweek()
        if gw is None:
            return "No active gameweek", {}
        rows = self.session.exec(
            select(ManagersSquad, PlayerStat)
            .where(ManagersSquad.manager_id == manager_id)
            .where(ManagersSquad.gw_id == gw.gw_id)
            .join(PlayerStat, (PlayerStat.player_id == ManagersSquad.player_id) & (
                PlayerStat.gw_id == ManagersSquad.gw_id
            ))
        ).all()
        total_points = sum(ps.total_points for (_, ps) in rows)
        details = [
            {
                "player_id": str(ps.player_id),
                "gw_id": str(ps.gw_id),
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
            .join(PlayerStat, (PlayerStat.player_id == ManagersSquad.player_id) & (
                PlayerStat.gw_id == ManagersSquad.gw_id
            ))
            .where(ManagersSquad.gw_id == gw.gw_id)
        ).all()
        totals: dict[UUID, int] = defaultdict(int)
        names: dict[UUID, str] = {}
        for mid, name, pts in rows:
            totals[mid] += pts
            names[mid] = name
        items = sorted(
            ({"manager_id": str(mid), "squad_name": names[mid], "points": pts} 
            for mid, pts in totals.items()),
            key=lambda i: i["points"],
            reverse=True,
        )
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], total

    def make_transfer(self, manager_id: UUID, player_out_id: int, player_in_id: int, gw_id: int | None) -> str:
        gw = self.session.get(Gameweek, gw_id) if gw_id is not None else None
        if gw is None:
            gw = self.get_active_gameweek()
        if gw is None:
            return "No active gameweek"

        current_ids = [
            t
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
            
        # Create new squad list with the transfer applied
        new_squad = [pid for pid in current_ids if pid != player_out_id] + [player_in_id]
        
        # Validate position quotas
        is_valid, error_msg = self._validate_position_quotas(new_squad)
        if not is_valid:
            return error_msg

        # Ensure manager exists
        manager = self.session.get(Manager, manager_id)
        if not manager:
            return "Manager not found"

        # Ensure gameweek state exists (carry over free transfers up to 2; carry budget)
        state = self.session.exec(
            select(ManagerGameweekState)
            .where(ManagerGameweekState.manager_id == manager_id)
            .where(ManagerGameweekState.gw_id == gw.gw_id)
        ).first()
        if state is None:
            # Determine previous gw state for carry over
            prev_gw = self.session.exec(
                select(Gameweek).where(Gameweek.gw_number == gw.gw_number - 1)
            ).first()
            prev_state = None
            if prev_gw is not None:
                prev_state = self.session.exec(
                    select(ManagerGameweekState)
                    .where(ManagerGameweekState.manager_id == manager_id)
                    .where(ManagerGameweekState.gw_id == prev_gw.gw_id)
                ).first()
            free_transfers = 1 if prev_state is None else min(2, prev_state.free_transfers + 1)
            start_budget: Decimal
            if prev_state is not None:
                start_budget = prev_state.transfers_budget
            else:
                # Initialize from manager.wallet if available, else zero
                start_budget = Decimal(manager.wallet or 0)
            state = ManagerGameweekState(
                manager_id=manager_id,
                gw_id=gw.gw_id,
                free_transfers=free_transfers,
                transfers_made=0,
                transfers_budget=start_budget,
                created_at=gw.start_date or gw.updated_at or gw.created_at,
                updated_at=None,
            )
            self.session.add(state)
            self.session.commit()

        # Pricing for this GW (fallback to current_price)
        price_out_row = self.session.exec(
            select(PlayerPrice).where(
                (PlayerPrice.player_id == player_out_id) & (PlayerPrice.gw_id == gw.gw_id)
            )
        ).first()
        price_in_row = self.session.exec(
            select(PlayerPrice).where(
                (PlayerPrice.player_id == player_in_id) & (PlayerPrice.gw_id == gw.gw_id)
            )
        ).first()
        out_price: Decimal
        in_price: Decimal
        if price_out_row is not None:
            out_price = price_out_row.price
        else:
            out_player = self.session.get(Player, player_out_id)
            if out_player is None:
                return "Player out not found"
            out_price = Decimal(out_player.current_price)
        if price_in_row is not None:
            in_price = price_in_row.price
        else:
            in_player = self.session.get(Player, player_in_id)
            if in_player is None:
                return "Player in not found"
            in_price = Decimal(in_player.current_price)

        # Budget check: End Bank = Start Bank + Price(Out) – Price(In)
        start_bank: Decimal = state.transfers_budget
        end_bank: Decimal = start_bank + out_price - in_price
        if end_bank < 0:
            return "Insufficient budget for transfer"

        # Transfer rights: use FT if available, else extra transfer (records for points deduction)
        if state.free_transfers > 0:
            state.free_transfers -= 1
        # Each transfer increments transfers_made
        state.transfers_made += 1
        state.transfers_budget = end_bank
        state.updated_at = gw.updated_at or gw.end_date or gw.start_date or state.updated_at
        self.session.add(state)

        # Record transfer
        self.session.add(
            Transfer(
                manager_id=manager_id,
                player_in_id=player_in_id,
                player_out_id=player_out_id,
                gw_id=gw.gw_id,
            )
        )

        # Apply the swap in current squad
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

    def substitute(self, manager_id: UUID, player_out_id: int, player_in_id: int) -> str:
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
            
        # Get all current starters
        starters = self.session.exec(
            select(ManagersSquad.player_id, Player.position_id)
            .where(
                (ManagersSquad.manager_id == manager_id)
                & (ManagersSquad.gw_id == gw.gw_id)
                & (ManagersSquad.is_starter == True)  # noqa: E712
            )
            .join(Player, Player.player_id == ManagersSquad.player_id)
        ).all()
        
        # Calculate new starters after substitution
        starter_ids = set(pid for pid, _ in starters)
        if out_row.is_starter:
            starter_ids.remove(player_out_id)
            starter_ids.add(player_in_id)
        elif in_row.is_starter:
            starter_ids.remove(player_in_id)
            starter_ids.add(player_out_id)
            
        # Validate starting 11 positions
        pos_counts: dict[int, int] = defaultdict(int)
        for _, pos_id in starters:
            pos_counts[pos_id] += 1
            
        # Basic formation validation (at least 1 GK, 3 DEF, 2 MID, 1 FWD)
        min_required = {1: 1, 2: 3, 3: 2, 4: 1}
        if any(pos_counts.get(pid, 0) < count for pid, count in min_required.items()):
            return "Invalid formation after substitution"
            
        # Apply the substitution
        out_row.is_starter, in_row.is_starter = in_row.is_starter, out_row.is_starter
        self.session.add(out_row)
        self.session.add(in_row)
        self.session.commit()
        return "OK"

    def update_transfer(self, manager_id: UUID, transfer_id: UUID, player_out_id: int, player_in_id: int) -> str:
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



