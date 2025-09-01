from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, update
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
                return False, f"No more than 3 players from the same team. Team {team.team_name} has {team_counts[team.team_id]} players"

        required = {1: 2, 2: 5, 3: 5, 4: 3}  # GK: 2, DEF: 5, MID: 5, FWD: 3
        position_names = {1: "Goalkeeper", 2: "Defender", 3: "Midfielder", 4: "Forward"}
        
        # Check each position requirement and build specific error message
        quota_errors = []
        for pos_id, required_count in required.items():
            current_count = pos_counts.get(pos_id, 0)
            if current_count != required_count:
                quota_errors.append(f"{position_names[pos_id]}: {current_count}/{required_count}")
        
        if quota_errors:
            return False, f"Position quotas not satisfied. Required: {', '.join(quota_errors)}"
            
        return True, "OK"

    def get_active_gameweek(self) -> Gameweek | None:
        # Latest active-like gameweek (treat legacy statuses as active)
        return self.session.exec(
            select(Gameweek)
            .where(Gameweek.status.in_(["active", "Ongoing", "open"]))
            .order_by(Gameweek.gw_number.desc())
            .limit(1)
        ).first()

    def get_scoring_gameweek(self) -> Gameweek | None:
        """Return the gameweek that should be used for scoring display.

        - If an "active" gameweek exists, use it (matches underway).
        - Otherwise, use the latest "completed" gameweek (during transfer/open week).
        - As a last resort, fall back to the latest "open" gameweek.
        """
        # Prefer an actually playing gameweek
        active = self.session.exec(
            select(Gameweek)
            .where(Gameweek.status.in_(["active", "Ongoing"]))
            .order_by(Gameweek.gw_number.desc())
            .limit(1)
        ).first()
        if active is not None:
            return active

        # Otherwise show points from the most recent completed GW
        completed = self.session.exec(
            select(Gameweek)
            .where(Gameweek.status == "completed")
            .order_by(Gameweek.gw_number.desc())
            .limit(1)
        ).first()
        if completed is not None:
            return completed

        # Finally, fall back to open (e.g., very first GW before any matches)
        return self.get_open_gameweek()

    def get_open_gameweek(self) -> Gameweek | None:
        """Return the latest transfer-week gameweek (status == 'open')."""
        return self.session.exec(
            select(Gameweek)
            .where(Gameweek.status == "open")
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
                return f"No more than 3 players from the same team. Team {team.team_name} has {team_counts[team.team_id]} players"

        required = {1: 2, 2: 5, 3: 5, 4: 3}
        position_names = {1: "Goalkeeper", 2: "Defender", 3: "Midfielder", 4: "Forward"}
        
        # Check each position requirement and build specific error message
        quota_errors = []
        for pos_id, required_count in required.items():
            current_count = pos_counts.get(pos_id, 0)
            if current_count != required_count:
                quota_errors.append(f"{position_names[pos_id]}: {current_count}/{required_count}")
        
        if quota_errors:
            return f"Position quotas not satisfied. Required: {', '.join(quota_errors)}"

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
        
        # Create or update manager gameweek state to ensure free transfers are available
        existing_state = self.session.exec(
            select(ManagerGameweekState)
            .where(ManagerGameweekState.manager_id == manager_id)
            .where(ManagerGameweekState.gw_id == gw.gw_id)
        ).first()
        
        if existing_state is None:
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
            
            free_transfers = 1 if prev_state is None else min(3, prev_state.free_transfers + 1)
            
            new_state = ManagerGameweekState(
                manager_id=manager_id,
                gw_id=gw.gw_id,
                free_transfers=free_transfers,
                transfers_made=0,
                squad_points=0,
                captain_bonus=0,
                transfer_penalty=0,
                total_gw_points=0,
                bench_points=0,
                vice_captain_used=False,
                created_at=gw.start_date or gw.updated_at or gw.created_at,
                updated_at=None,
            )
            self.session.add(new_state)
        
        self.session.commit()
        
        # Calculate initial squad points after saving
        from app.scoring.service import ScoringService
        scoring_service = ScoringService(self.session)
        scoring_service.update_manager_gameweek_points(manager_id, gw.gw_id)
        
        return "OK"

    def get_squad(self, manager_id: UUID) -> tuple[str | None, list[dict[str, Any]]]:
        # Keep showing the editable squad for the current GW (can be 'open'),
        # but compute displayed totals from the latest scoring GW.
        gw = self.get_active_gameweek()
        if gw is None:
            return "No active gameweek", []
        scoring_gw = self.get_scoring_gameweek()
        if scoring_gw is None:
            scoring_gw = gw
        
        # Get squad players with their stats
        rows = self.session.exec(
            select(ManagersSquad, Player, PlayerStat)
            .where(ManagersSquad.manager_id == manager_id)
            .where(ManagersSquad.gw_id == gw.gw_id)
            .join(Player, Player.player_id == ManagersSquad.player_id)
            .join(PlayerStat, (PlayerStat.player_id == ManagersSquad.player_id) & 
                  (PlayerStat.gw_id == ManagersSquad.gw_id))
        ).all()
        
        # Get manager gameweek state for points (use scoring GW)
        state = self.session.exec(
            select(ManagerGameweekState)
            .where(ManagerGameweekState.manager_id == manager_id)
            .where(ManagerGameweekState.gw_id == scoring_gw.gw_id)
        ).first()
        
        data = [
            {
                "player_id": str(player.player_id),
                "name": player.player_fullname,
                "position_id": player.position_id,
                "team_id": player.team_id,
                "is_captain": ms.is_captain,
                "is_vice_captain": ms.is_vice_captain,
                "is_starter": ms.is_starter,
                "points": player_stat.total_points,
            }
            for (ms, player, player_stat) in rows
        ]
        
        # Add manager gameweek points (from scoring GW)
        is_completed = (scoring_gw.status or "").lower() == "completed"
        squad_info = {
            "squad_players": data,
            "gameweek": gw.gw_id,
            "scoring_gameweek": scoring_gw.gw_id,
            "squad_points": state.squad_points if state else 0,
            # Hide penalties until the gameweek is completed
            "transfer_penalty": (state.transfer_penalty if (state and is_completed) else 0),
            "total_gw_points": state.total_gw_points if state else 0,
            "free_transfers": state.free_transfers if state else 0,
            "transfers_made": state.transfers_made if state else 0,
        }
        
        return None, squad_info

    def overview(self, manager_id: UUID) -> tuple[str | None, dict[str, Any]]:
        # Always compute overview from the latest scoring GW
        gw = self.get_scoring_gameweek()
        if gw is None:
            return "No active gameweek", {}
        
        # Get manager gameweek state for proper points calculation
        state = self.session.exec(
            select(ManagerGameweekState)
            .where(ManagerGameweekState.manager_id == manager_id)
            .where(ManagerGameweekState.gw_id == gw.gw_id)
        ).first()
        
        if not state:
            return "No gameweek state found", {}
        
        # Get squad players with their stats (for the scoring GW)
        rows = self.session.exec(
            select(ManagersSquad, PlayerStat)
            .where(ManagersSquad.manager_id == manager_id)
            .where(ManagersSquad.gw_id == gw.gw_id)
            .join(PlayerStat, (PlayerStat.player_id == ManagersSquad.player_id) & (
                PlayerStat.gw_id == ManagersSquad.gw_id
            ))
        ).all()
        
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
        
        is_completed = (gw.status or "").lower() == "completed"
        return None, {
            "squad_points": state.squad_points,
            # Hide penalties until the gameweek is completed
            "transfer_penalty": state.transfer_penalty if is_completed else 0,
            "total_gw_points": state.total_gw_points,
            "free_transfers": state.free_transfers,
            "transfers_made": state.transfers_made,
            "scoring_gameweek": gw.gw_id,
            "players": details
        }

    def leaderboard(self, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
        # Use scoring GW so that during an 'open' window the last completed GW shows
        current_gw = self.get_scoring_gameweek()
        if current_gw is None:
            return [], 0

        # Points for the current gameweek
        current_rows = self.session.exec(
            select(
                Manager.manager_id,
                Manager.squad_name,
                ManagerGameweekState.total_gw_points,
            )
            .join(ManagerGameweekState, ManagerGameweekState.manager_id == Manager.manager_id)
            .where(ManagerGameweekState.gw_id == current_gw.gw_id)
        ).all()

        # Cumulative points up to and including the current gameweek
        cumulative_rows = self.session.exec(
            select(
                ManagerGameweekState.manager_id,
                func.sum(ManagerGameweekState.total_gw_points),
            )
            .join(Gameweek, Gameweek.gw_id == ManagerGameweekState.gw_id)
            .where(Gameweek.gw_number <= current_gw.gw_number)
            .group_by(ManagerGameweekState.manager_id)
        ).all()

        manager_to_cumulative: dict[UUID, int] = {
            mid: int(sum_pts or 0) for (mid, sum_pts) in cumulative_rows
        }

        items: list[dict[str, Any]] = []
        for (mid, name, gw_points) in current_rows:
            items.append(
                {
                    "manager_id": str(mid),
                    "squad_name": name,
                    "gameweek_points": int(gw_points or 0),
                    "cumulative_points": manager_to_cumulative.get(mid, int(gw_points or 0)),
                }
            )

        # If a manager has cumulative points but no row in current_rows (edge), include with 0 gw points
        known_ids = {m[0] for m in current_rows}
        if len(known_ids) != len(manager_to_cumulative):
            for mid, total_pts in manager_to_cumulative.items():
                if mid in known_ids:
                    continue
                manager = self.session.get(Manager, mid)
                items.append(
                    {
                        "manager_id": str(mid),
                        "squad_name": manager.squad_name if manager else "",
                        "gameweek_points": 0,
                        "cumulative_points": int(total_pts or 0),
                    }
                )

        # Sort by cumulative points desc
        items.sort(key=lambda i: i["cumulative_points"], reverse=True)

        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], total

    def make_transfer(self, manager_id: UUID, player_out_id: int, player_in_id: int, gw_id: int | None) -> str:
        # Transfers are only allowed during the transfer week (status == 'open')
        gw = self.session.get(Gameweek, gw_id) if gw_id is not None else None
        print(gw)
        if gw is None:
            gw = self.get_open_gameweek()
        if gw is None:
            return "No transfer window currently open"
        if gw.status != "open":
            return "Transfers are only allowed during the transfer week"

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

        # Get gameweek state (should already exist from squad creation)
        state = self.session.exec(
            select(ManagerGameweekState)
            .where(ManagerGameweekState.manager_id == manager_id)
            .where(ManagerGameweekState.gw_id == gw.gw_id)
        ).first()
        if state is None:
            return "No gameweek state found. Please save your squad first."

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

        # Budget check and update manager wallet: End Bank = Wallet + Price(Out) – Price(In)
        start_bank: Decimal = Decimal(manager.wallet or 0)
        end_bank: Decimal = start_bank + out_price - in_price
        if end_bank < 0:
            return "Insufficient budget for transfer"

        # Transfer rights: use FT if available, else extra transfer (records for points deduction)
        if state.free_transfers > 0:
            state.free_transfers -= 1
        else:
            # Extra transfer - add penalty points
            state.transfer_penalty += 4
        
        # Each transfer increments transfers_made
        state.transfers_made += 1
        state.updated_at = gw.updated_at or gw.end_date or gw.start_date or state.updated_at
        self.session.add(state)
        # Persist manager wallet update
        manager.wallet = float(end_bank)
        self.session.add(manager)

        # Record transfer
        from datetime import datetime
        self.session.add(
            Transfer(
                manager_id=manager_id,
                player_in_id=player_in_id,
                player_out_id=player_out_id,
                gw_id=gw.gw_id,
                player_in_price=in_price,
                player_out_price=out_price,
                transfer_time=datetime.now(),
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
        
        # Update manager gameweek points after transfer (penalty only applied at GW end)
        from app.scoring.service import ScoringService
        scoring_service = ScoringService(self.session)
        scoring_service.update_manager_gameweek_points(manager_id, gw.gw_id)
        
        return "OK"

    def substitute(self, manager_id: UUID, player_out_id: int, player_in_id: int
    ) -> str:
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
        
        # Fetch player position details for fast-path checks
        out_player = self.session.get(Player, out_row.player_id)
        in_player = self.session.get(Player, in_row.player_id)
        if out_player is None or in_player is None:
            return "Player data not found"
        
        # Substitution must be between one starter and one bench player
        if out_row.is_starter == in_row.is_starter:
            return "Substitution requires one starter and one bench player"
        
        # Fast path: if both players share the same position, formation cannot change.
        # Perform the swap immediately without heavy validation.
        if out_player.position_id == in_player.position_id:
            out_row.is_starter, in_row.is_starter = in_row.is_starter, out_row.is_starter
            self.session.add(out_row)
            self.session.add(in_row)
            self.session.commit()
            return "OK"
            
        # Get current formation before substitution
        current_formation = self.session.exec(
            select(ManagersSquad.player_id, Player.position_id, ManagersSquad.is_starter)
            .where(
                (ManagersSquad.manager_id == manager_id)
                & (ManagersSquad.gw_id == gw.gw_id)
            )
            .join(Player, Player.player_id == ManagersSquad.player_id)
        ).all()
        
        # Calculate new formation after substitution
        pos_counts: dict[int, int] = defaultdict(int)
        starter_count = 0
        
        for squad_player_id, position_id, is_starter in current_formation:
            # For the players being substituted, use their new starter status
            if squad_player_id == player_out_id:
                if in_row.is_starter:  # out_row gets in_row's status
                    pos_counts[position_id] += 1
                    starter_count += 1
            elif squad_player_id == player_in_id:
                if out_row.is_starter:  # in_row gets out_row's status
                    pos_counts[position_id] += 1
                    starter_count += 1
            # For all other players, use their current status
            elif is_starter:
                pos_counts[position_id] += 1
                starter_count += 1
            
        # Validate we have exactly 11 starters
        if starter_count != 11:
            return f"Invalid formation after substitution. Expected 11 starters, got {starter_count}"

        # Basic formation validation (at least 1 GK, 3 DEF, 2 MID, 1 FWD)
        min_required = {1: 1, 2: 3, 3: 2, 4: 1}
        position_names = {1: "Goalkeeper", 2: "Defender", 3: "Midfielder", 4: "Forward"}
        
        # Check each position requirement and build specific error message
        missing_positions = []
        excess_positions = []
        for pos_id, min_count in min_required.items():
            current_count = pos_counts.get(pos_id, 0)
            if current_count < min_count:
                missing_positions.append(f"{position_names[pos_id]}: have {current_count}, need {min_count}")
            elif current_count > min_count + 2:  # Allow some flexibility but not too much
                excess_positions.append(f"{position_names[pos_id]}: have {current_count}, max {min_count + 2}")
        
        if missing_positions:
            return f"Formation invalid after substitution - too few: {', '.join(missing_positions)}"
        if excess_positions:
            return f"Formation invalid after substitution - too many: {', '.join(excess_positions)}"
            
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



