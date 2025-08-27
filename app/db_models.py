from __future__ import annotations

import secrets
import time
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql.sqltypes import DateTime, Numeric
from sqlmodel import Field, SQLModel


def uuid7() -> UUID:
    """Generate a sortable UUID (version 7) using 60-bit ms timestamp.

    Layout (MSB → LSB):
    - 60 bits: timestamp in milliseconds since Unix epoch
    - 4 bits: version (0111)
    - 2 bits: variant (10)
    - 62 bits: random
    """
    ts_ms = int(time.time_ns() // 1_000_000)
    if ts_ms >= (1 << 60):
        raise ValueError("Timestamp exceeds 60-bit space for UUIDv7")
    rand62 = secrets.randbits(62)
    value = (ts_ms << 68) | (0x7 << 64) | (0b10 << 62) | rand62
    return UUID(int=value)


class Admin(SQLModel, table=True):
    __tablename__ = "admins"

    admin_id: int = Field(primary_key=True)
    username: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime


class Event(SQLModel, table=True):
    __tablename__ = "events"

    event_id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    player_id: int = Field(foreign_key="players.player_id")
    gw_id: int = Field(foreign_key="gameweeks.gw_id")
    event_type: str
    fixture_id: int = Field(foreign_key="fixtures.fixture_id")
    minute: int
    created_at: datetime
    updated_at: datetime


class Fixture(SQLModel, table=True):
    __tablename__ = "fixtures"

    fixture_id: int = Field(primary_key=True)
    gw_id: int = Field(foreign_key="gameweeks.gw_id")
    home_team_id: int = Field(foreign_key="teams.team_id")
    away_team_id: int = Field(foreign_key="teams.team_id")
    date: datetime
    home_team_score: int = 0
    away_team_score: int = 0
    created_at: datetime
    updated_at: datetime


class Gameweek(SQLModel, table=True):
    __tablename__ = "gameweeks"

    gw_id: int = Field(primary_key=True)
    gw_number: int
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class ManagerActivityLog(SQLModel, table=True):
    __tablename__ = "manager_activity_logs"

    log_id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    manager_id: UUID = Field(foreign_key="managers.manager_id")
    action: str
    context: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    ip_adress: str | None = None
    user_agent: str | None = None
    created_at: datetime


class ManagerGameweekState(SQLModel, table=True):
    __tablename__ = "manager_gameweek_state"

    manager_id: UUID = Field(primary_key=True, foreign_key="managers.manager_id")
    gw_id: int = Field(primary_key=True, foreign_key="gameweeks.gw_id")
    free_transfers: int = 1
    transfers_made: int = 0
    squad_points: int = 0
    captain_bonus: int = 0
    transfer_penalty: int = 0
    total_gw_points: int = 0
    bench_points: int = 0
    vice_captain_used: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class Manager(SQLModel, table=True):
    __tablename__ = "managers"

    manager_id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    mng_firstname: str
    mng_lastname: str
    squad_name: str
    email: str
    hashed_password: str
    birthdate: datetime | None = None
    city: str | None = None
    fav_team_id: int | None = Field(default=None, foreign_key="teams.team_id")
    fav_player_id: int | None = Field(default=None, foreign_key="players.player_id")
    created_at: datetime
    updated_at: datetime
    mng_datapoint: str
    wallet: float = 0.0


class ManagersSquad(SQLModel, table=True):
    __tablename__ = "managers_squad"

    manager_id: UUID = Field(primary_key=True, foreign_key="managers.manager_id")
    player_id: int = Field(primary_key=True, foreign_key="players.player_id")
    gw_id: int = Field(primary_key=True, foreign_key="gameweeks.gw_id")
    is_captain: bool = False
    is_vice_captain: bool = False
    is_starter: bool = False


class PlayerPrice(SQLModel, table=True):
    __tablename__ = "player_prices"

    player_id: int = Field(primary_key=True, foreign_key="players.player_id")
    gw_id: int = Field(primary_key=True, foreign_key="gameweeks.gw_id")
    price: Decimal = Field(sa_column=Column(Numeric(5, 2), nullable=False))
    transfers_in: int
    transfers_out: int
    net_transfers: int
    updated_at: datetime
    selected: int = 0


class PlayerStat(SQLModel, table=True):
    __tablename__ = "player_stats"

    player_id: int = Field(primary_key=True, foreign_key="players.player_id")
    gw_id: int = Field(primary_key=True, foreign_key="gameweeks.gw_id")
    total_points: int = 0
    goals_scored: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    clean_sheets: int = 0
    bonus_points: int = 0
    minutes_played: int = 0
    created_at: datetime
    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    started: bool = False


class Player(SQLModel, table=True):
    __tablename__ = "players"

    player_id: int = Field(primary_key=True)
    player_firstname: str
    player_lastname: str
    player_fullname: str
    player_pic_url: str
    team_id: int = Field(foreign_key="teams.team_id")
    position_id: int = Field(foreign_key="positions.position_id")
    initial_price: Decimal = Field(sa_column=Column(Numeric(5, 2), nullable=False))
    current_price: Decimal = Field(sa_column=Column(Numeric(5, 2), nullable=False))
    is_active: bool


class Position(SQLModel, table=True):
    __tablename__ = "positions"

    position_id: int = Field(primary_key=True)
    position_name: str


class ScoringRule(SQLModel, table=True):
    __tablename__ = "scoring_rules"

    event_type: str = Field(primary_key=True)
    position_id: int = Field(primary_key=True, foreign_key="positions.position_id")
    points: int


class Team(SQLModel, table=True):
    __tablename__ = "teams"

    team_id: int = Field(primary_key=True)
    team_name: str
    team_shortname: str
    team_logo_url: str
    created_at: datetime
    updated_at: datetime


class Transfer(SQLModel, table=True):
    __tablename__ = "transfers"

    transfer_id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    manager_id: UUID = Field(foreign_key="managers.manager_id")
    player_in_id: int = Field(foreign_key="players.player_id")
    player_out_id: int = Field(foreign_key="players.player_id")
    gw_id: int = Field(foreign_key="gameweeks.gw_id")
    player_in_price: Decimal = Field(sa_column=Column(Numeric(5, 2), nullable=False))
    player_out_price: Decimal = Field(sa_column=Column(Numeric(5, 2), nullable=False))
    transfer_time: datetime = Field(
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )


