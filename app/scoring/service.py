from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.db_models import ManagerGameweekState, ManagersSquad, Player, PlayerStat

# Scoring rules constants based on the CSV file
SCORING_RULES = {
    "goal": {1: 10, 2: 6, 3: 5, 4: 4},  # GK: 10, DEF: 6, MID: 5, FWD: 4
    "assist": {1: 3, 2: 3, 3: 3, 4: 3},  # All positions: 3
    "clean_sheet": {1: 4, 2: 4, 3: 1, 4: 0},  # GK/DEF: 4, MID: 1, FWD: 0
    "yellow": {1: -1, 2: -1, 3: -1, 4: -1},  # All positions: -1
    "red": {1: -3, 2: -3, 3: -3, 4: -3},  # All positions: -3
    "started": {1: 1, 2: 1, 3: 1, 4: 1},  # All positions: 1
    "penalty_miss": {1: -2, 2: -2, 3: -2, 4: -2},  # All positions: -2
    "penalty_save": {1: 5, 2: 5, 3: 5, 4: 5},  # All positions: 5
    "own_goal": {1: -2, 2: -2, 3: -2, 4: -2},  # All positions: -2
}


class ScoringService:
    def __init__(self, session: Session):
        self.session = session
        self._scoring_rules = SCORING_RULES

    def calculate_player_points(self, player_stat: PlayerStat, player: Player) -> int:
        """Calculate total points for a player based on their stats and position."""
        total_points = 0
        
        # Goals
        if player_stat.goals_scored > 0:
            goal_points = self._scoring_rules.get('goal', {}).get(player.position_id, 0)
            total_points += player_stat.goals_scored * goal_points
        
        # Assists
        if player_stat.assists > 0:
            assist_points = self._scoring_rules.get('assist', {}).get(player.position_id, 0)
            total_points += player_stat.assists * assist_points
        
        # Clean sheets
        if player_stat.clean_sheets > 0:
            clean_sheet_points = self._scoring_rules.get('clean_sheet', {}).get(player.position_id, 0)
            total_points += player_stat.clean_sheets * clean_sheet_points
        
        # Yellow cards
        if player_stat.yellow_cards > 0:
            yellow_points = self._scoring_rules.get('yellow', {}).get(player.position_id, 0)
            total_points += player_stat.yellow_cards * yellow_points
        
        # Red cards
        if player_stat.red_cards > 0:
            red_points = self._scoring_rules.get('red', {}).get(player.position_id, 0)
            total_points += player_stat.red_cards * red_points
        
        # Started bonus
        if player_stat.started:
            started_points = self._scoring_rules.get('started', {}).get(player.position_id, 0)
            total_points += started_points
        
        # Bonus points (from external source)
        total_points += player_stat.bonus_points
        
        return total_points

    def recalculate_gameweek_points(self, gw_id: int) -> None:
        """Recalculate points for all players in a specific gameweek."""
        # Get all player stats for the gameweek
        player_stats = self.session.exec(
            select(PlayerStat, Player)
            .join(Player, Player.player_id == PlayerStat.player_id)
            .where(PlayerStat.gw_id == gw_id)
        ).all()
        
        for player_stat, player in player_stats:
            # Calculate new total points
            new_total_points = self.calculate_player_points(player_stat, player)
            
            # Update the player stat
            player_stat.total_points = new_total_points
            self.session.add(player_stat)
        
        self.session.commit()

    def points_for_gameweek(self, gameweek: str) -> list[dict[str, Any]]:
        """Get points for all players in a gameweek."""
        try:
            gw_id = int(gameweek)
        except ValueError:
            return []
            
        rows = self.session.exec(
            select(PlayerStat, Player)
            .join(Player, Player.player_id == PlayerStat.player_id)
            .where(PlayerStat.gw_id == gw_id)
        ).all()
        
        return [
            {
                "player_id": str(player_stat.player_id),
                "player_name": player.player_fullname,
                "position_id": player.position_id,
                "gw_id": str(player_stat.gw_id),
                "total_points": player_stat.total_points,
                "goals": player_stat.goals_scored,
                "assists": player_stat.assists,
                "clean_sheets": player_stat.clean_sheets,
                "yellow_cards": player_stat.yellow_cards,
                "red_cards": player_stat.red_cards,
                "bonus_points": player_stat.bonus_points,
                "minutes_played": player_stat.minutes_played,
                "started": player_stat.started,
            }
            for player_stat, player in rows
        ]

    def get_scoring_rules(self) -> dict[str, dict[int, int]]:
        """Get current scoring rules."""
        return self._scoring_rules.copy()

    def update_player_points(self, player_id: int, gw_id: int) -> None:
        """Update points for a specific player in a specific gameweek."""
        player_stat = self.session.exec(
            select(PlayerStat).where(
                (PlayerStat.player_id == player_id) & (PlayerStat.gw_id == gw_id)
            )
        ).first()
        
        if not player_stat:
            return
            
        player = self.session.get(Player, player_id)
        if not player:
            return
            
        # Calculate new total points
        new_total_points = self.calculate_player_points(player_stat, player)
        
        # Update the player stat
        player_stat.total_points = new_total_points
        self.session.add(player_stat)
        self.session.commit()

    def update_player_stats_and_points(
        self, 
        player_id: int, 
        gw_id: int, 
        goals: int = None,
        assists: int = None,
        yellow_cards: int = None,
        red_cards: int = None,
        clean_sheets: int = None,
        bonus_points: int = None,
        minutes_played: int = None,
        started: bool = None
    ) -> None:
        """Update player stats and automatically recalculate points."""
        player_stat = self.session.exec(
            select(PlayerStat).where(
                (PlayerStat.player_id == player_id) & (PlayerStat.gw_id == gw_id)
            )
        ).first()
        
        if not player_stat:
            return
            
        # Update provided stats
        if goals is not None:
            player_stat.goals_scored = goals
        if assists is not None:
            player_stat.assists = assists
        if yellow_cards is not None:
            player_stat.yellow_cards = yellow_cards
        if red_cards is not None:
            player_stat.red_cards = red_cards
        if clean_sheets is not None:
            player_stat.clean_sheets = clean_sheets
        if bonus_points is not None:
            player_stat.bonus_points = bonus_points
        if minutes_played is not None:
            player_stat.minutes_played = minutes_played
        if started is not None:
            player_stat.started = started
            
        # Get player for point calculation
        player = self.session.get(Player, player_id)
        if not player:
            return
            
        # Automatically recalculate points
        new_total_points = self.calculate_player_points(player_stat, player)
        player_stat.total_points = new_total_points
        
        self.session.add(player_stat)
        self.session.commit()
        
        # Update all managers who have this player in their squad
        managers_with_player = self.session.exec(
            select(ManagersSquad.manager_id)
            .where(ManagersSquad.player_id == player_id)
            .where(ManagersSquad.gw_id == gw_id)
        ).all()
        
        for manager_id in managers_with_player:
            self.update_manager_gameweek_points(manager_id, gw_id)

    def calculate_manager_squad_points(self, manager_id: UUID, gw_id: int) -> int:
        """Calculate total points for a manager's squad in a specific gameweek."""
        # Get all players in manager's squad for this gameweek
        squad_players = self.session.exec(
            select(ManagersSquad, PlayerStat)
            .join(PlayerStat, (PlayerStat.player_id == ManagersSquad.player_id) & 
                  (PlayerStat.gw_id == ManagersSquad.gw_id))
            .where(ManagersSquad.manager_id == manager_id)
            .where(ManagersSquad.gw_id == gw_id)
        ).all()
        
        total_squad_points = 0
        for squad_player, player_stat in squad_players:
            # Add player points to squad total
            total_squad_points += player_stat.total_points
            
            # Apply captain bonus (double points for captain)
            if squad_player.is_captain:
                total_squad_points += player_stat.total_points  # Double the points
        
        return total_squad_points

    def update_manager_gameweek_points(self, manager_id: UUID, gw_id: int) -> None:
        """Update manager's gameweek points (squad_points and total_gw_points)."""
        # Get manager gameweek state
        state = self.session.exec(
            select(ManagerGameweekState)
            .where(ManagerGameweekState.manager_id == manager_id)
            .where(ManagerGameweekState.gw_id == gw_id)
        ).first()
        
        if not state:
            return
            
        # Calculate squad points
        squad_points = self.calculate_manager_squad_points(manager_id, gw_id)
        
        # Update state
        state.squad_points = squad_points
        state.total_gw_points = squad_points - state.transfer_penalty
        
        self.session.add(state)
        self.session.commit()

    def recalculate_all_manager_points(self, gw_id: int) -> None:
        """Recalculate points for all managers in a specific gameweek."""
        # Get all managers who have squads in this gameweek
        manager_ids = self.session.exec(
            select(ManagersSquad.manager_id)
            .where(ManagersSquad.gw_id == gw_id)
            .distinct()
        ).all()
        
        for manager_id in manager_ids:
            self.update_manager_gameweek_points(manager_id, gw_id)



