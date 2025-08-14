from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SquadPlayerSelection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: int
    is_captain: bool = False
    is_vice_captain: bool = False
    is_starter: bool = True


class SquadSaveRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gw_id: int | None = None
    players: list[SquadPlayerSelection] = Field(default_factory=list)


class TransferRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_out_id: int
    player_in_id: int
    gw_id: int | None = None





