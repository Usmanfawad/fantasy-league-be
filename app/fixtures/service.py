from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.db_models import Fixture, Gameweek


class FixturesService:
    def __init__(self, session: Session):
        self.session = session

    def list_fixtures(self) -> list[dict]:
        rows = self.session.exec(
            select(Fixture, Gameweek).join(Gameweek, Gameweek.gw_id == Fixture.gw_id)
        ).all()
        return [
            {
                "fixture_id": f.fixture_id,
                "gw_id": str(f.gw_id),
                "home_team_id": f.home_team_id,
                "away_team_id": f.away_team_id,
                "date": f.date.isoformat(),
                "home_team_score": f.home_team_score,
                "away_team_score": f.away_team_score,
                "gw_status": gw.status,
            }
            for (f, gw) in rows
        ]

    def fixtures_for_gw(self, gameweek_id: str) -> list[dict]:
        gw_id = int(gameweek_id)
        rows = self.session.exec(select(Fixture).where(Fixture.gw_id == gw_id)).all()
        return [
            {
                "fixture_id": f.fixture_id,
                "gw_id": str(f.gw_id),
                "home_team_id": f.home_team_id,
                "away_team_id": f.away_team_id,
                "date": f.date.isoformat(),
                "home_team_score": f.home_team_score,
                "away_team_score": f.away_team_score,
            }
            for f in rows
        ]

    def results_for_gw(self, gameweek_id: str) -> list[dict]:
        gw_id = int(gameweek_id)
        rows = self.session.exec(select(Fixture).where(Fixture.gw_id == gw_id)).all()
        return [
            {
                "fixture_id": f.fixture_id,
                "home_team_score": f.home_team_score,
                "away_team_score": f.away_team_score,
            }
            for f in rows
        ]


