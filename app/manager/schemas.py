from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class SquadPlayerSelection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: UUID
    is_captain: bool = False
    is_vice_captain: bool = False
    is_starter: bool = True


class SquadSaveRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gw_id: UUID | None = None
    players: list[SquadPlayerSelection] = Field(default_factory=list)


class TransferRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_out_id: UUID
    player_in_id: UUID
    gw_id: UUID | None = None





