from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from faker import Faker
from sqlmodel import Session, select

from app.db_models import (
    Fixture,
    Gameweek,
    Manager,
    ManagersSquad,
    Player,
    PlayerPrice,
    PlayerStat,
    Position,
    ScoringRule,
    Team,
    Transfer,
)

# Use scoring rules constants
from app.scoring.service import SCORING_RULES
from app.utils.db import engine

fake = Faker()
random.seed(42)
Faker.seed(42)


def seed_positions(session: Session) -> list[Position]:
    existing = session.exec(select(Position)).all()
    if existing:
        return existing
    positions = [
        Position(position_id=1, position_name="Goalkeeper"),
        Position(position_id=2, position_name="Defender"),
        Position(position_id=3, position_name="Midfielder"),
        Position(position_id=4, position_name="Forward"),
    ]
    session.add_all(positions)
    # Don't commit here - let the main function handle it
    return positions


def seed_teams(session: Session, count: int = 6) -> list[Team]:
    existing = session.exec(select(Team)).all()
    if existing:
        return existing
    
    teams_data = [
        ("Wydad Athletic Club", "WAC"),
        ("Raja Club Athletic", "RCA"),
        ("FUS Rabat", "FUS"),
        ("Maghreb Association Sportive", "MAS"),
        ("Moghreb Athletic Tetouan", "MAT"),
        ("Olympic Club Safi", "OCS")
    ]
    
    teams: list[Team] = []
    for i, (name, shortname) in enumerate(teams_data, 1):
        teams.append(
            Team(
                team_id=i,
                team_name=name,
                team_shortname=shortname,
                team_logo_url=fake.image_url(),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
    session.add_all(teams)
    # Don't commit here - let the main function handle it
    return teams


def seed_players(
    session: Session, teams: list[Team], positions: list[Position], per_team: int = 15
) -> list[Player]:
    existing = session.exec(select(Player)).all()
    if existing:
        return existing
    players: list[Player] = []
    for team in teams:
        for _ in range(per_team):
            first = fake.first_name()
            last = fake.last_name()
            pos = random.choice(positions)
            initial = Decimal(random.randrange(45, 120)) / Decimal(10)
            current = initial + Decimal(random.randrange(-10, 15)) / Decimal(10)
            players.append(
                Player(
                    player_firstname=first,
                    player_lastname=last,
                    player_fullname=f"{first} {last}",
                    player_pic_url=fake.image_url(),
                    team_id=team.team_id,
                    position_id=pos.position_id,
                    initial_price=initial.quantize(Decimal("0.00")),
                    current_price=current.quantize(Decimal("0.00")),
                    is_active=True,
                )
            )
    session.add_all(players)
    # Don't commit here - let the main function handle it
    return players


def seed_gameweeks(session: Session, count: int = 3) -> list[Gameweek]:
    existing = session.exec(select(Gameweek)).all()
    if existing:
        return existing
    base = datetime.now(UTC)
    gws: list[Gameweek] = []
    for i in range(1, count + 1):
        start = base + timedelta(days=(i - 1) * 7)
        end = start + timedelta(days=6)
        gws.append(
            Gameweek(
                gw_number=i,
                start_date=start.replace(tzinfo=None),
                end_date=end.replace(tzinfo=None),
                status="active" if i == 1 else "Upcoming",
                created_at=datetime.now(UTC).replace(tzinfo=None),
                updated_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
    session.add_all(gws)
    # Don't commit here - let the main function handle it
    return gws


def seed_fixtures(session: Session, gws: list[Gameweek], teams: list[Team]) -> list[Fixture]:
    existing = session.exec(select(Fixture)).all()
    if existing:
        return existing
    fixtures: list[Fixture] = []
    for gw in gws:
        team_ids = [t.team_id for t in teams]
        random.shuffle(team_ids)
        for i in range(0, len(team_ids), 2):
            if i + 1 >= len(team_ids):
                break
            home, away = team_ids[i], team_ids[i + 1]
            fixtures.append(
                Fixture(
                    fixture_id=len(fixtures) + 1,
                    gw_id=gw.gw_id,
                    home_team_id=home,
                    away_team_id=away,
                    date=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=gw.gw_number),
                    home_team_score=0,
                    away_team_score=0,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                    updated_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
    session.add_all(fixtures)
    # Don't commit here - let the main function handle it
    return fixtures


def seed_scoring_rules(session: Session, positions: list[Position]) -> None:
    existing = session.exec(select(ScoringRule)).all()
    if existing:
        return

    
    rules: list[ScoringRule] = []
    for event_type, position_mapping in SCORING_RULES.items():
        for position_id, points in position_mapping.items():
            rules.append(
                ScoringRule(
                    event_type=event_type,
                    position_id=position_id,
                    points=points,
                )
            )
    
    session.add_all(rules)
    # Don't commit here - let the main function handle it


def seed_managers(
    session: Session, teams: list[Team], players: list[Player], count: int = 5
) -> list[Manager]:
    """No-op: managers are not created by the seeder. Return existing managers only."""
    return session.exec(select(Manager)).all()


def seed_manager_squads(
    session: Session, managers: list[Manager], players: list[Player], gws: list[Gameweek]
) -> None:
    existing = session.exec(select(ManagersSquad)).first()
    if existing:
        return
    for manager in managers:
        for gw in gws:
            # Select 5 players like notebook does
            selected_players = random.sample(players, k=5)
            captain = random.choice(selected_players)
            others = [p for p in selected_players if p != captain]
            vice_captain = random.choice(others) if others else None
            
            for player in selected_players:
                session.add(
                    ManagersSquad(
                        manager_id=manager.manager_id,
                        player_id=player.player_id,
                        gw_id=gw.gw_id,
                        is_captain=player == captain,
                        is_vice_captain=player == vice_captain,
                        is_starter=True,
                    )
                )
    # Don't commit here - let the main function handle it


def seed_prices_and_stats(
    session: Session, players: list[Player], gws: list[Gameweek]
) -> None:
    if session.exec(select(PlayerPrice)).first() or session.exec(select(PlayerStat)).first():
        return
    for gw in gws:
        for player in players:
            session.add(
                PlayerPrice(
                    player_id=player.player_id,
                    gw_id=gw.gw_id,
                    price=player.current_price,
                    transfers_in=random.randrange(0, 5000),
                    transfers_out=random.randrange(0, 5000),
                    net_transfers=random.randrange(-1000, 1000),
                    updated_at=datetime.now(UTC).replace(tzinfo=None),
                    selected=random.randrange(0, 50000),
                )
            )
            started = random.random() < 0.7
            minutes = random.choice([0, 30, 60, 90]) if started else 0
            goals = random.randint(0, 3) if minutes > 0 else 0
            assists = random.randint(0, 2) if minutes > 0 else 0
            yellow = random.randint(0, 1) if minutes > 0 else 0
            red = random.randint(0, 1) if yellow == 1 else 0
            clean = random.randint(0, 1) if minutes >= 60 else 0
            bonus = random.randint(0, 3) if minutes > 0 else 0
            
            
            total_points = 0
            
            # Goals
            goal_points = SCORING_RULES.get('goal', {}).get(player.position_id, 0)
            total_points += goals * goal_points
            
            # Assists
            assist_points = SCORING_RULES.get('assist', {}).get(player.position_id, 0)
            total_points += assists * assist_points
            
            # Clean sheets
            clean_sheet_points = SCORING_RULES.get('clean_sheet', {}).get(player.position_id, 0)
            total_points += clean * clean_sheet_points
            
            # Yellow cards
            yellow_points = SCORING_RULES.get('yellow', {}).get(player.position_id, 0)
            total_points += yellow * yellow_points
            
            # Red cards
            red_points = SCORING_RULES.get('red', {}).get(player.position_id, 0)
            total_points += red * red_points
            
            # Started bonus
            if started:
                started_points = SCORING_RULES.get('started', {}).get(player.position_id, 0)
                total_points += started_points
            
            # Bonus points (from external source)
            total_points += bonus
            session.add(
                PlayerStat(
                    player_id=player.player_id,
                    gw_id=gw.gw_id,
                    total_points=total_points,
                    goals_scored=goals,
                    assists=assists,
                    yellow_cards=yellow,
                    red_cards=red,
                    clean_sheets=clean,
                    bonus_points=bonus,
                    minutes_played=minutes,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                    updated_at=None,
                    started=started,
                )
            )
    # Don't commit here - let the main function handle it


def seed_transfers(session: Session, managers: list[Manager], players: list[Player], gws: list[Gameweek]) -> None:
    if session.exec(select(Transfer)).first():
        return
    if not managers or not players or not gws:
        return
    for _ in range(50):
        manager = random.choice(managers)
        player_out = random.choice(players)
        player_in = random.choice([p for p in players if p.player_id != player_out.player_id])
        gw = random.choice(gws)
        # Find latest price rows for selected GW
        price_out = session.exec(
            select(PlayerPrice).where(
                (PlayerPrice.player_id == player_out.player_id) & (PlayerPrice.gw_id == gw.gw_id)
            )
        ).first()
        price_in = session.exec(
            select(PlayerPrice).where(
                (PlayerPrice.player_id == player_in.player_id) & (PlayerPrice.gw_id == gw.gw_id)
            )
        ).first()
        session.add(
            Transfer(
                manager_id=manager.manager_id,
                player_in_id=player_in.player_id,
                player_out_id=player_out.player_id,
                gw_id=gw.gw_id,
                player_in_price=(price_in.price if price_in else player_in.current_price),
                player_out_price=(price_out.price if price_out else player_out.current_price),
                transfer_time=datetime.now(UTC).replace(tzinfo=None),
            )
        )
    # Don't commit here - let the main function handle it


def main() -> None:
    with Session(engine) as session:
        positions = seed_positions(session)
        teams = seed_teams(session)  # Will use 6 Moroccan teams
        players = seed_players(session, teams, positions, per_team=7)  # Reduced players per team
        gws = seed_gameweeks(session, count=3)  # Match notebook's 3 gameweeks
        fixtures = seed_fixtures(session, gws, teams)
        seed_scoring_rules(session, positions)
        managers = seed_managers(session, teams, players, count=5)
        seed_manager_squads(session, managers, players, gws)
        seed_prices_and_stats(session, players, gws)
        seed_transfers(session, managers, players, gws)
        
        # Always commit - if no changes, this will be a no-op
        try:
            session.commit()
            print(
                f"Seeded: {len(positions)} positions, {len(teams)} teams, {len(players)} players, "
                f"{len(gws)} gameweeks, {len(fixtures)} fixtures, {len(managers)} managers."
            )
        except Exception as e:
            # If commit fails due to no changes, that's okay
            print(f"Seeding completed (no new data to commit): {e}")


if __name__ == "__main__":
    main()


