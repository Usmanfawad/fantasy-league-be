from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ORM_CONFIG = ConfigDict(from_attributes=True)


class Admin(BaseModel):
    model_config = ORM_CONFIG

    admin_id: int
    username: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime


class Event(BaseModel):
    model_config = ORM_CONFIG

    event_id: UUID
    player_id: int
    gw_id: int
    event_type: str
    fixture_id: int
    minute: int
    created_at: datetime
    updated_at: datetime


class Fixture(BaseModel):
    model_config = ORM_CONFIG

    fixture_id: int
    gw_id: int
    home_team_id: int
    away_team_id: int
    date: datetime
    home_team_score: int = Field(default=0)
    away_team_score: int = Field(default=0)
    created_at: datetime
    updated_at: datetime


class Gameweek(BaseModel):
    model_config = ORM_CONFIG

    gw_id: int
    gw_number: int
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class ManagerActivityLog(BaseModel):
    model_config = ORM_CONFIG

    log_id: int
    manager_id: UUID
    action: str
    context: dict[str, Any] | None = None
    ip_adress: str | None = None
    user_agent: str | None = None
    created_at: datetime


class Manager(BaseModel):
    model_config = ORM_CONFIG

    manager_id: UUID
    mng_firstname: str
    mng_lastname: str
    squad_name: str
    email: str
    hashed_password: str
    birthdate: datetime
    city: str | None = None
    fav_team_id: int | None = None
    fav_player_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    mng_datapoint: str
    wallet: float = Field(default=0.0)


class ManagerSquad(BaseModel):
    model_config = ORM_CONFIG

    manager_id: UUID
    player_id: int
    gw_id: int
    is_captain: bool = Field(default=False)
    is_vice_captain: bool = Field(default=False)
    is_starter: bool = Field(default=False)


class PlayerPrice(BaseModel):
    model_config = ORM_CONFIG

    player_id: int
    gw_id: int
    price: Decimal
    transfers_in: int
    transfers_out: int
    net_transfers: int
    updated_at: datetime
    selected: int = Field(default=0)


class PlayerStat(BaseModel):
    model_config = ORM_CONFIG

    player_id: int
    gw_id: int
    total_points: int = Field(default=0)
    goals_scored: int = Field(default=0)
    assists: int = Field(default=0)
    yellow_cards: int = Field(default=0)
    red_cards: int = Field(default=0)
    clean_sheets: int = Field(default=0)
    bonus_points: int = Field(default=0)
    minutes_played: int = Field(default=0)
    created_at: datetime
    updated_at: datetime | None = None
    started: bool = Field(default=False)


class Player(BaseModel):
    model_config = ORM_CONFIG

    player_id: int
    player_firstname: str
    player_lastname: str
    player_fullname: str
    player_pic_url: str
    team_id: int
    position_id: int
    initial_price: Decimal
    current_price: Decimal
    is_active: bool


class Position(BaseModel):
    model_config = ORM_CONFIG

    position_id: int
    position_name: str


class ScoringRule(BaseModel):
    model_config = ORM_CONFIG

    event_type: str
    position_id: int
    points: int


class Team(BaseModel):
    model_config = ORM_CONFIG

    team_id: int
    team_name: str
    team_shortname: str
    team_logo_url: str
    created_at: datetime
    updated_at: datetime


class Transfer(BaseModel):
    model_config = ORM_CONFIG

    transfer_id: UUID
    manager_id: UUID
    player_in_id: int
    player_out_id: int
    gw_id: int
    player_in_price: Decimal
    player_out_price: Decimal
    transfer_time: datetime


__all__ = [
    "Admin",
    "Event",
    "Fixture",
    "Gameweek",
    "Manager",
    "ManagerActivityLog",
    "ManagerSquad",
    "Player",
    "PlayerPrice",
    "PlayerStat",
    "Position",
    "ScoringRule",
    "Team",
    "Transfer",
]


