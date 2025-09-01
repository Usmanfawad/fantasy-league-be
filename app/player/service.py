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
        """Get player stats with gameweek_points for the current GW and cumulative_points up to it."""
        # Determine current (reference) gameweek
        current_gw: Gameweek | None = None
        if gw_id is not None:
            current_gw = self.session.get(Gameweek, gw_id)
        if current_gw is None:
            current_gw = self.session.exec(
                select(Gameweek).where(Gameweek.status == "open").order_by(Gameweek.gw_number.desc()).limit(1)
            ).first()
        if current_gw is None:
            current_gw = self.session.exec(
                select(Gameweek).order_by(Gameweek.gw_number.desc()).limit(1)
            ).first()
        if current_gw is None:
            return [], 0

        # Fetch players per filters
        player_stmt = select(Player)
        if team_id is not None:
            player_stmt = player_stmt.where(Player.team_id == team_id)
        if position_id is not None:
            player_stmt = player_stmt.where(Player.position_id == position_id)
        players_all = self.session.exec(player_stmt).all()
        total = len(players_all)

        player_ids = [p.player_id for p in players_all]

        # Current GW stats map
        stats_rows = []
        if player_ids:
            stats_rows = self.session.exec(
                select(PlayerStat)
                .where(PlayerStat.gw_id == current_gw.gw_id)
                .where(PlayerStat.player_id.in_(player_ids))
            ).all()
        current_map: dict[int, PlayerStat] = {s.player_id: s for s in stats_rows}

        # Cumulative points up to current GW number
        from sqlalchemy import and_
        cum_rows = []
        if player_ids:
            cum_rows = self.session.exec(
                select(PlayerStat.player_id, func.sum(PlayerStat.total_points))
                .join(Gameweek, Gameweek.gw_id == PlayerStat.gw_id)
                .where(and_(PlayerStat.player_id.in_(player_ids), Gameweek.gw_number <= current_gw.gw_number))
                .group_by(PlayerStat.player_id)
            ).all()
        cumulative_map: dict[int, int] = {pid: int(total or 0) for (pid, total) in cum_rows}

        # Build sortable items
        items: list[dict[str, Any]] = []
        for p in players_all:
            ps = current_map.get(p.player_id)
            gameweek_points = int(ps.total_points) if ps else 0
            cumulative_points = cumulative_map.get(p.player_id, gameweek_points)
            team = self.session.get(Team, p.team_id)
            position = self.session.get(Position, p.position_id)
            items.append(
                {
                    "player_id": str(p.player_id),
                    "fullname": p.player_fullname,
                    "team_name": team.team_name if team else None,
                    "position_name": position.position_name if position else None,
                    "current_price": str(p.current_price),
                    "cumulative_points": cumulative_points,
                    "gameweek_points": gameweek_points,
                    "goals": (ps.goals_scored if ps else 0),
                    "assists": (ps.assists if ps else 0),
                    "bonus_points": (ps.bonus_points if ps else 0),
                    "yellow_cards": (ps.yellow_cards if ps else 0),
                    "red_cards": (ps.red_cards if ps else 0),
                    "clean_sheets": (ps.clean_sheets if ps else 0),
                    "minutes_played": (ps.minutes_played if ps else 0),
                    "selection_percentage": self._get_selection_percentage(p.player_id, current_gw.gw_id),
                }
            )

        # Sorting
        sort = (sort or "cumulative_points").lower()
        # Always stabilize by player_id to avoid "weird" ordering when primary keys tie
        items.sort(key=lambda it: int(it["player_id"]))

        if sort == "player_id":
            # Explicit sort by player_id (ascending)
            # Already stabilized above; sort again to be explicit/no-op
            items.sort(key=lambda it: int(it["player_id"]))
        else:
            def sort_value(item: dict[str, Any]) -> float:
                try:
                    if sort == "gameweek_points":
                        return float(item["gameweek_points"]) 
                    if sort == "goals":
                        return float(item["goals"]) 
                    if sort == "assists":
                        return float(item["assists"]) 
                    if sort == "bonus_points":
                        return float(item["bonus_points"]) 
                    if sort == "price":
                        return float(item["current_price"]) 
                    if sort == "minutes_played":
                        return float(item["minutes_played"]) 
                    if sort == "clean_sheets":
                        return float(item["clean_sheets"]) 
                    if sort == "selection_percentage":
                        return float(item["selection_percentage"]) 
                    # default cumulative
                    return float(item["cumulative_points"]) 
                except Exception:
                    return 0.0

            items.sort(key=sort_value, reverse=True)
        page_items = items[(page - 1) * page_size : (page - 1) * page_size + page_size]
        return page_items, total



