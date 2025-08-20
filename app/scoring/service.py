from __future__ import annotations

from sqlmodel import Session, select

from app.db_models import PlayerStat


class ScoringService:
    def __init__(self, session: Session):
        self.session = session

    def points_for_gameweek(self, gameweek: int) -> list[dict]:
        rows = self.session.exec(select(PlayerStat).where(PlayerStat.gw_id == gameweek)).all()
        return [
            {
                "player_id": r.player_id,
                "gw_id": r.gw_id,
                "points": r.total_points,
            }
            for r in rows
        ]



