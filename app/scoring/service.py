from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.db_models import PlayerStat


class ScoringService:
    def __init__(self, session: Session):
        self.session = session

    def points_for_gameweek(self, gameweek: str) -> list[dict]:
        gw = UUID(gameweek)
        rows = self.session.exec(select(PlayerStat).where(PlayerStat.gw_id == gw)).all()
        return [
            {
                "player_id": str(r.player_id),
                "gw_id": str(r.gw_id),
                "points": r.total_points,
            }
            for r in rows
        ]



