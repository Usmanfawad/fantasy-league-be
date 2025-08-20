from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from app.db_models import Gameweek, Player, PlayerPrice, PlayerStat, Position, Team


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
        price_map: dict[int, tuple[str, int]] = {}
        points_map: dict[int, int] = {}
        if latest_gw_id is not None and rows:
            player_ids = [p.player_id for (p, _t, _pos) in rows]
            prices = self.session.exec(
                select(PlayerPrice).where(
                    (PlayerPrice.gw_id == latest_gw_id)
                    & (PlayerPrice.player_id.in_(player_ids))
                )
            ).all()
            for pp in prices:
                price_map[int(pp.player_id)] = (str(pp.price), int(pp.selected))

            stats = self.session.exec(
                select(PlayerStat).where(
                    (PlayerStat.gw_id == latest_gw_id)
                    & (PlayerStat.player_id.in_(player_ids))
                )
            ).all()
            for ps in stats:
                points_map[int(ps.player_id)] = int(ps.total_points)

        # Compose response
        data: list[dict[str, Any]] = []
        for (p, t, pos) in rows:
            price, selected = price_map.get(int(p.player_id), (str(p.current_price), 0))
            total_points = points_map.get(int(p.player_id), 0)
            data.append(
                {
                    "player_id": p.player_id,
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
            "player_id": p.player_id,
            "player_fullname": p.player_fullname,
            "position_name": pos.position_name,
            "team_name": t.team_name,
            "price": price,
            "player_pic_url": p.player_pic_url,
            "total_points": total_points,
            "selected_percentage": selected,
        }

    def get_player_stats(self, player_id: int) -> list[dict[str, Any]] | None:
        p = self.session.get(Player, player_id)
        if not p:
            return None
        stats = self.session.exec(select(PlayerStat).where(PlayerStat.player_id == player_id)).all()
        return [
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

    def players_stats(
        self,
        gw_id: int | None,
        team_id: int | None,
        position_id: int | None,
        sort: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
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
        def sort_key(item: tuple[PlayerStat, Player]):
            ps, p = item
            if sort == "gameweek_points":
                return ps.total_points
            if sort == "goals":
                return ps.goals_scored
            if sort == "assists":
                return ps.assists
            if sort == "bonus_points":
                return ps.bonus_points
            if sort == "price":
                # price not on PlayerStat; fallback to current price on Player
                try:
                    return float(p.current_price)
                except Exception:
                    return 0.0
            # default cumulative_points: approximate with total_points here
            return ps.total_points

        rows = sorted(rows, key=sort_key, reverse=True)
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
        return data, total



