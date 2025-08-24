from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from app.db_models import (
    Gameweek,
    Manager,
    Player,
    PlayerPrice,
    PlayerStat,
    Position,
    Team,
)


class PlayerService:
    def __init__(self, session: Session):
        self.session = session

    def list_players(
        self,
        q: str | None,
        team_id: int | None,
        position_id: int | None,
        active_only: bool,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        # Base query with joins for team and position names
        stmt = (
            select(Player, Team, Position)
            .join(Team, Team.team_id == Player.team_id)
            .join(Position, Position.position_id == Player.position_id)
        )
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

        # Total before pagination
        total = len(self.session.exec(stmt).all())

        # Pagination
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = self.session.exec(stmt).all()

        # Determine most recent gameweek id (if any)
        latest_gw_id = self.session.exec(
            select(Gameweek.gw_id).order_by(Gameweek.gw_id.desc()).limit(1)
        ).first()

        # Build lookup maps for prices and stats for the latest gameweek
        price_map: dict[UUID, tuple[str, int]] = {}
        points_map: dict[UUID, int] = {}
        if latest_gw_id is not None and rows:
            player_ids = [p.player_id for (p, _t, _pos) in rows]
            prices = self.session.exec(
                select(PlayerPrice).where(
                    (PlayerPrice.gw_id == latest_gw_id)
                    & (PlayerPrice.player_id.in_(player_ids))
                )
            ).all()
            for pp in prices:
                price_map[pp.player_id] = (str(pp.price), int(pp.selected))

            stats = self.session.exec(
                select(PlayerStat).where(
                    (PlayerStat.gw_id == latest_gw_id)
                    & (PlayerStat.player_id.in_(player_ids))
                )
            ).all()
            for ps in stats:
                points_map[ps.player_id] = int(ps.total_points)

        # Compose response
        data: list[dict[str, Any]] = []
        for (p, t, pos) in rows:
            price, selected = price_map.get(p.player_id, (str(p.current_price), 0))
            total_points = points_map.get(p.player_id, 0)
            data.append(
                {
                    "player_id": str(p.player_id),
                    "player_fullname": p.player_fullname,
                    "position_name": pos.position_name,
                    "team_name": t.team_name,
                    "price": str(price),
                    "player_pic_url": p.player_pic_url,
                    "total_points": total_points,
                    "selected_percentage": selected,
                }
            )
        return data, total

    def get_player(self, player_id: int) -> dict[str, Any] | None:
        row = self.session.exec(
            select(Player, Team, Position)
            .where(Player.player_id == player_id)
            .join(Team, Team.team_id == Player.team_id)
            .join(Position, Position.position_id == Player.position_id)
        ).first()
        if not row:
            return None
        p, t, pos = row

        latest_gw_id = self.session.exec(
            select(Gameweek.gw_id).order_by(Gameweek.gw_id.desc()).limit(1)
        ).first()

        price: str
        selected: int
        total_points: int
        price = str(p.current_price)
        selected = 0
        total_points = 0
        if latest_gw_id is not None:
            pp = self.session.exec(
                select(PlayerPrice).where(
                    (PlayerPrice.player_id == player_id) & (PlayerPrice.gw_id == latest_gw_id)
                )
            ).first()
            if pp:
                price = str(pp.price)
                selected = int(pp.selected)
            ps = self.session.exec(
                select(PlayerStat).where(
                    (PlayerStat.player_id == player_id) & (PlayerStat.gw_id == latest_gw_id)
                )
            ).first()
            if ps:
                total_points = int(ps.total_points)

        return {
            "player_id": str(p.player_id),
            "player_fullname": p.player_fullname,
            "position_name": pos.position_name,
            "team_name": t.team_name,
            "price": price,
            "player_pic_url": p.player_pic_url,
            "total_points": total_points,
            "selected_percentage": selected,
        }

    def get_player_stats(self, player_id: int) -> list[dict[str, Any]] | None:
        """Get all stats for a player across all gameweeks."""
        p = self.session.get(Player, player_id)
        if not p:
            return None
            
        # Get all stats for this player
        stats = self.session.exec(select(PlayerStat).where(PlayerStat.player_id == player_id)).all()
        
        # Get player's team and position
        team = self.session.get(Team, p.team_id)
        position = self.session.get(Position, p.position_id)
        
        return [
            {
                # Basic info
                "gw_id": str(s.gw_id),
                "player_name": p.player_fullname,
                "team": team.team_name if team else None,
                "position": position.position_name if position else None,
                
                # Core stats
                "total_points": s.total_points,
                "minutes_played": s.minutes_played,
                "started": s.started,
                
                # Attacking stats
                "goals_scored": s.goals_scored,
                "assists": s.assists,
                
                # Defensive stats
                "clean_sheets": s.clean_sheets,
                
                # Disciplinary
                "yellow_cards": s.yellow_cards,
                "red_cards": s.red_cards,
                
                # Bonus
                "bonus_points": s.bonus_points,
                
                # Timestamps
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None
            }
            for s in stats
        ]

    def _calculate_cumulative_points(self, player_id: int, upto_gw_id: int | None) -> int:
        """Calculate total points up to the specified gameweek UUID; if None, sum all."""
        stmt = select(PlayerStat).where(PlayerStat.player_id == player_id)
        if upto_gw_id is not None:
            gw = self.session.get(Gameweek, upto_gw_id)
            if gw is not None:
                # Join to Gameweek to filter by gw_number ordering
                from sqlalchemy import and_
                stmt = select(PlayerStat).join(Gameweek, Gameweek.gw_id == PlayerStat.gw_id).where(
                    and_(PlayerStat.player_id == player_id, Gameweek.gw_number <= gw.gw_number)
                )
        stats = self.session.exec(stmt).all()
        return sum(stat.total_points for stat in stats)

    def _get_selection_percentage(self, player_id: int, gw_id: int) -> float:
        """Calculate selection percentage for a player in a given gameweek."""
        price_data = self.session.exec(
            select(PlayerPrice)
            .where(PlayerPrice.player_id == player_id)
            .where(PlayerPrice.gw_id == gw_id)
        ).first()
        
        if not price_data:
            return 0.0
            
        # Get total number of managers for percentage calculation
        total_managers = self.session.exec(
            select(func.count(Manager.manager_id))
        ).first()
        
        if not total_managers:
            return 0.0
            
        return (price_data.selected / total_managers) * 100 if total_managers > 0 else 0.0

    def players_stats(
        self,
        gw_id: int | None,
        team_id: int | None,
        position_id: int | None,
        sort: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get player stats with all required fields from the leaderboard spec."""
        stmt = select(PlayerStat, Player).join(Player, Player.player_id == PlayerStat.player_id)
        if gw_id is not None:
            stmt = stmt.where(PlayerStat.gw_id == gw_id)
        if team_id is not None:
            stmt = stmt.where(Player.team_id == team_id)
        if position_id is not None:
            stmt = stmt.where(Player.position_id == position_id)

        rows = self.session.exec(stmt).all()
        total = len(rows)
        # Sorting per spec: cumulative_points (default), gameweek_points, goals, assists, bonus_points, price
        def sort_key(item: tuple[PlayerStat, Player]) -> float:
            ps, p = item
            current_gw: int | None = gw_id or ps.gw_id
            
            if sort == "gameweek_points":
                return float(ps.total_points)
            if sort == "goals":
                return float(ps.goals_scored)
            if sort == "assists":
                return float(ps.assists)
            if sort == "bonus_points":
                return float(ps.bonus_points)
            if sort == "price":
                try:
                    return float(p.current_price)
                except Exception:
                    return 0.0
            if sort == "minutes_played":
                return float(ps.minutes_played)
            if sort == "clean_sheets":
                return float(ps.clean_sheets)
            if sort == "selection_percentage":
                return self._get_selection_percentage(p.player_id, ps.gw_id)
                
            # default: cumulative_points
            return float(self._calculate_cumulative_points(p.player_id, current_gw))

        rows = sorted(rows, key=sort_key, reverse=True)
        rows = rows[(page - 1) * page_size : (page - 1) * page_size + page_size]
        data = [
            {
                "player_id": str(p.player_id),
                "fullname": p.player_fullname,
                "team_name": self.session.get(Team, p.team_id).team_name,
                "position_name": self.session.get(Position, p.position_id).position_name,
                "current_price": str(p.current_price),
                "cumulative_points": ps.total_points,  # We should calculate this across all GWs
                "gameweek_points": ps.total_points,
                "goals": ps.goals_scored,
                "assists": ps.assists,
                "bonus_points": ps.bonus_points,
                "yellow_cards": ps.yellow_cards,
                "red_cards": ps.red_cards,
                "clean_sheets": ps.clean_sheets,
                "minutes_played": ps.minutes_played,
                "selection_percentage": self._get_selection_percentage(p.player_id, ps.gw_id)
            }
            for (ps, p) in rows
        ]
        return data, total



