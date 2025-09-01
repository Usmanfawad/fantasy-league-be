"""Service layer for managing fixtures and gameweek transitions."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from app.db_models import (
    Fixture,
    Gameweek,
    Manager,
    ManagerGameweekState,
    ManagersSquad,
    PlayerPrice,
    Team,
    Transfer,
)
from app.scoring.service import ScoringService


class FixturesService:
    def __init__(self, session: Session):
        self.session = session

    def list_fixtures(self) -> list[dict]:
        HomeTeam = aliased(Team)
        AwayTeam = aliased(Team)
        rows = self.session.exec(
            select(
                Fixture,
                Gameweek,
                HomeTeam.team_name,
                AwayTeam.team_name,
            )
            .join(Gameweek, Gameweek.gw_id == Fixture.gw_id)
            .join(HomeTeam, HomeTeam.team_id == Fixture.home_team_id)
            .join(AwayTeam, AwayTeam.team_id == Fixture.away_team_id)
        ).all()
        return [
            {
                "fixture_id": f.fixture_id,
                "gw_id": str(f.gw_id),
                "home_team_id": f.home_team_id,
                "home_team_name": home_name,
                "away_team_id": f.away_team_id,
                "away_team_name": away_name,
                "date": f.date.isoformat(),
                "home_team_score": f.home_team_score,
                "away_team_score": f.away_team_score,
                "gw_status": gw.status,
            }
            for (f, gw, home_name, away_name) in rows
        ]

    def fixtures_for_gw(self, gameweek_id: str) -> list[dict]:
        gw_id = int(gameweek_id)
        HomeTeam = aliased(Team)
        AwayTeam = aliased(Team)
        rows = self.session.exec(
            select(
                Fixture,
                HomeTeam.team_name,
                AwayTeam.team_name,
            )
            .where(Fixture.gw_id == gw_id)
            .join(HomeTeam, HomeTeam.team_id == Fixture.home_team_id)
            .join(AwayTeam, AwayTeam.team_id == Fixture.away_team_id)
        ).all()
        return [
            {
                "fixture_id": f.fixture_id,
                "gw_id": str(f.gw_id),
                "home_team_id": f.home_team_id,
                "home_team_name": home_name,
                "away_team_id": f.away_team_id,
                "away_team_name": away_name,
                "date": f.date.isoformat(),
                "home_team_score": f.home_team_score,
                "away_team_score": f.away_team_score,
            }
            for (f, home_name, away_name) in rows
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

    def get_first_fixture_time(self, gw_id: int) -> datetime | None:
        """Get the kickoff time of the first fixture in a gameweek."""
        fixture = self.session.exec(
            select(Fixture)
            .where(Fixture.gw_id == gw_id)
            .order_by(Fixture.date)
            .limit(1)
        ).first()
        return fixture.date if fixture else None

    def get_last_fixture_time(self, gw_id: int) -> datetime | None:
        """Get the kickoff time of the last fixture in a gameweek."""
        fixture = self.session.exec(
            select(Fixture)
            .where(Fixture.gw_id == gw_id)
            .order_by(Fixture.date.desc())
            .limit(1)
        ).first()
        return fixture.date if fixture else None

    def copy_squads_to_next_gameweek(self, completed_gw_id: int) -> None:
        """
        Copy all manager squads from completed gameweek to next gameweek.
        Also resets manager gameweek states with new free transfers.
        """
        # Resolve completed GW and find the true next GW by gw_number
        completed_gw = self.session.get(Gameweek, completed_gw_id)
        if not completed_gw:
            return
        next_gw = self.session.exec(
            select(Gameweek)
            .where(Gameweek.gw_number > completed_gw.gw_number)
            .order_by(Gameweek.gw_number)
            .limit(1)
        ).first()
        
        if not next_gw:
            return

        # Get all squads from completed gameweek
        squads = self.session.exec(
            select(ManagersSquad)
            .where(ManagersSquad.gw_id == completed_gw_id)
        ).all()

        now = datetime.utcnow()

        # Copy each squad to new gameweek
        for squad in squads:
            new_squad = ManagersSquad(
                manager_id=squad.manager_id,
                gw_id=next_gw.gw_id,
                player_id=squad.player_id,
                is_captain=squad.is_captain,
                is_vice_captain=squad.is_vice_captain,
                is_starter=squad.is_starter
            )
            self.session.add(new_squad)

        # Get unique manager IDs and create manager gameweek states
        unique_manager_ids = set(squad.manager_id for squad in squads)
        for manager_id in unique_manager_ids:
            # Check if manager gameweek state already exists to avoid duplicates
            existing_state = self.session.exec(
                select(ManagerGameweekState)
                .where(ManagerGameweekState.manager_id == manager_id)
                .where(ManagerGameweekState.gw_id == next_gw.gw_id)
            ).first()
            
            if not existing_state:
                # Carry over free transfers from the completed GW: new = min(3, prev_free + 1)
                prev_state = self.session.exec(
                    select(ManagerGameweekState)
                    .where(ManagerGameweekState.manager_id == manager_id)
                    .where(ManagerGameweekState.gw_id == completed_gw_id)
                ).first()
                prev_free = 1 if prev_state is None else int(prev_state.free_transfers or 0)
                new_free = 1 if prev_state is None else min(3, prev_free + 1)

                # Reset manager gameweek state for next GW
                new_state = ManagerGameweekState(
                    manager_id=manager_id,
                    gw_id=next_gw.gw_id,
                    free_transfers=new_free,
                    transfers_made=0,
                    squad_points=0,
                    captain_bonus=0,
                    transfer_penalty=0,
                    total_gw_points=0,
                    bench_points=0,
                    vice_captain_used=False,
                    created_at=now
                )
                self.session.add(new_state)

        self.session.commit()

    def update_player_prices(self, gw_id: int) -> None:
        """
        Update player prices based on transfer activity.
        Called during OPEN state to reflect market changes.
        """
        # Get all transfers for this gameweek
        transfers = self.session.exec(
            select(Transfer)
            .where(Transfer.gw_id == gw_id)
        ).all()

        # Calculate net transfers per player
        player_transfers: dict[int, dict] = {}
        for transfer in transfers:
            # Track transfers out
            if transfer.player_out_id not in player_transfers:
                player_transfers[transfer.player_out_id] = {"in": 0, "out": 0}
            player_transfers[transfer.player_out_id]["out"] += 1

            # Track transfers in
            if transfer.player_in_id not in player_transfers:
                player_transfers[transfer.player_in_id] = {"in": 0, "out": 0}
            player_transfers[transfer.player_in_id]["in"] += 1

        # Update prices in player_prices table
        now = datetime.utcnow()
        for player_id, transfer_counts in player_transfers.items():
            net_transfers = transfer_counts["in"] - transfer_counts["out"]
            
            # Get current price record
            price_record = self.session.exec(
                select(PlayerPrice)
                .where(PlayerPrice.player_id == player_id)
                .where(PlayerPrice.gw_id == gw_id)
            ).first()

            if price_record:
                price_record.transfers_in = transfer_counts["in"]
                price_record.transfers_out = transfer_counts["out"]
                price_record.net_transfers = net_transfers
                price_record.updated_at = now
                self.session.add(price_record)

        self.session.commit()

    def check_and_update_gameweek_states(self) -> None:
        """
        Check and automatically update gameweek states based on fixture times.
        This should be called regularly (e.g., by a scheduled task).
        """
        current_time = datetime.utcnow()

        # OPEN → ACTIVE transition
        open_gw = self.session.exec(
            select(Gameweek)
            .where(Gameweek.status == "open")
        ).first()

        if open_gw:
            first_fixture_time = self.get_first_fixture_time(open_gw.gw_id)
            if first_fixture_time and first_fixture_time <= current_time:
                open_gw.status = "active"
                open_gw.updated_at = current_time
                self.session.add(open_gw)

        # ACTIVE → COMPLETED transition
        active_gw = self.session.exec(
            select(Gameweek)
            .where(Gameweek.status == "active")
        ).first()

        if active_gw:
            last_fixture_time = self.get_last_fixture_time(active_gw.gw_id)
            # Check if 2 hours passed since last fixture
            if last_fixture_time:
                two_hours_after = last_fixture_time + timedelta(hours=2)
                if two_hours_after <= current_time:
                    active_gw.status = "completed"
                    active_gw.updated_at = current_time
                    self.session.add(active_gw)
                    # Persist completion before downstream operations rely on status
                    self.session.commit()

                    # Copy squads to next gameweek when completing current one
                    self.copy_squads_to_next_gameweek(active_gw.gw_id)

                    # Recalculate and persist all managers' points for the completed GW now
                    scoring = ScoringService(self.session)
                    scoring.recalculate_all_manager_points(active_gw.gw_id)

        self.session.commit()

    def validate_gameweek_action(
        self, gw_id: int, action_type: str
    ) -> tuple[bool, str]:
        """
        Validate if an action is allowed based on gameweek state.
        Returns (is_allowed, message).
        """
        gw = self.session.get(Gameweek, gw_id)
        if not gw:
            return False, "Invalid gameweek"
            
        allowed_actions = {
            "upcoming": ["view_fixtures"],
            "open": ["make_transfer", "set_captain", "arrange_squad", "view_fixtures"],
            "active": ["view_live_scores", "view_fixtures"],
            "completed": ["view_final_points", "view_fixtures"]
        }
        
        if action_type not in allowed_actions.get(gw.status, []):
            return False, f"Action {action_type} not allowed in {gw.status} state"
            
        return True, "OK"

    def update_live_scores(
        self, fixture_id: int, home_score: int, away_score: int
    ) -> bool:
        """
        Update live scores for a fixture during ACTIVE gameweek.
        Returns True if successful, False if fixture not found or not active.
        """
        # Get fixture and its gameweek
        fixture = self.session.get(Fixture, fixture_id)
        if not fixture:
            return False
            
        gw = self.session.get(Gameweek, fixture.gw_id)
        if not gw or gw.status != "active":
            return False
            
        # Update scores
        fixture.home_team_score = home_score
        fixture.away_team_score = away_score
        fixture.updated_at = datetime.utcnow()
        
        self.session.add(fixture)
        self.session.commit()
        
        return True

    def get_live_scores(self, gw_id: int) -> list[dict]:
        """
        Get live scores for all fixtures in an active gameweek.
        Returns list of fixture scores with team details.
        """
        # Get gameweek and verify it's active
        gw = self.session.get(Gameweek, gw_id)
        if not gw or gw.status != "active":
            return []
            
        # Get all fixtures with team details
        fixtures = self.session.exec(
            select(Fixture)
            .where(Fixture.gw_id == gw_id)
            .order_by(Fixture.date)
        ).all()
        
        return [
            {
                "fixture_id": f.fixture_id,
                "home_team_id": f.home_team_id,
                "away_team_id": f.away_team_id,
                "home_team_score": f.home_team_score,
                "away_team_score": f.away_team_score,
                "kickoff_time": f.date.isoformat(),
                "last_updated": f.updated_at.isoformat() if f.updated_at else None
            }
            for f in fixtures
        ]

    def open_transfer_window(self) -> tuple[bool, str, Gameweek | None]:
        """
        Open the transfer window for the next gameweek.
        Finds the oldest upcoming gameweek and opens it for transfers.
        
        Returns:
            tuple[bool, str, Gameweek | None]: (success, message, opened_gameweek)
        """
        # Check if any gameweek is already open
        open_gw = self.session.exec(
            select(Gameweek)
            .where(Gameweek.status == "open")
        ).first()
        
        if open_gw:
            msg = f"Cannot open window. GW {open_gw.gw_number} already open"
            return False, msg, None
            
        # Find oldest upcoming gameweek
        next_gw = self.session.exec(
            select(Gameweek)
            .where(Gameweek.status == "upcoming")
            .order_by(Gameweek.gw_number)
            .limit(1)
        ).first()
        
        if not next_gw:
            return False, "No upcoming gameweeks found", None
            
        # Open the transfer window
        next_gw.status = "open"
        next_gw.updated_at = datetime.utcnow()
        self.session.add(next_gw)
        
        # Initialize manager gameweek states if not already done
        manager_states = self.session.exec(
            select(ManagerGameweekState)
            .where(ManagerGameweekState.gw_id == next_gw.gw_id)
        ).all()
        
        if not manager_states:
            # Get all managers
            managers = self.session.exec(
                select(Manager)
            ).all()
            
            # Create initial states for all managers
            now = datetime.utcnow()
            for manager in managers:
                state = ManagerGameweekState(
                    manager_id=manager.manager_id,
                    gw_id=next_gw.gw_id,
                    free_transfers=1,
                    transfers_made=0,
                    squad_points=0,
                    captain_bonus=0,
                    transfer_penalty=0,
                    total_gw_points=0,
                    bench_points=0,
                    vice_captain_used=False,
                    created_at=now
                )
                self.session.add(state)
        
        self.session.commit()
        return True, f"Transfer window opened for GW {next_gw.gw_number}", next_gw

