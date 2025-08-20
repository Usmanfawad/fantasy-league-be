from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.dependencies import ManagerUser
from app.manager.schemas import SquadSaveRequest, TransferRequest
from app.manager.service import ManagerService
from app.user.models import UserRole
from app.utils.db import get_session
from app.utils.responses import ResponseSchema

manager_router = APIRouter(prefix="/managers", tags=["Managers"])


def _svc(session: Session) -> ManagerService:
    return ManagerService(session)


@manager_router.post("/{manager_id}/squad")
def save_squad(
    manager_id: int,
    body: SquadSaveRequest,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    if user.id != manager_id and user.role != UserRole.ADMIN:
        return ResponseSchema.forbidden("Cannot modify another manager's squad")

    svc = _svc(session)
    result = svc.validate_and_save_squad(
        manager_id,
        [p.model_dump() for p in (body.players or [])],
        body.gw_id,
    )
    if result == "OK":
        return ResponseSchema.success(message="Squad saved")
    return ResponseSchema.bad_request(result)


@manager_router.get("/{manager_id}/squad")
def get_squad(
    manager_id: int,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    if user.id != manager_id and user.role != UserRole.ADMIN:
        return ResponseSchema.forbidden("Cannot view another manager's squad")

    svc = _svc(session)
    err, data = svc.get_squad(manager_id)
    if err:
        return ResponseSchema.bad_request(err)
    return ResponseSchema.success(data=data)


@manager_router.put("/{manager_id}/squad")
def update_squad(
    manager_id: int,
    body: SquadSaveRequest,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    # Same validation and logic as save; we treat it as upsert for the GW
    return save_squad(manager_id, body, user, session)


@manager_router.get("/{manager_id}/overview")
def manager_overview(
    manager_id: int,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    if user.id != manager_id and user.role != UserRole.ADMIN:
        return ResponseSchema.forbidden("Cannot view another manager's overview")

    svc = _svc(session)
    err, data = svc.overview(manager_id)
    if err:
        return ResponseSchema.bad_request(err)
    return ResponseSchema.success(data=data)


@manager_router.get("/leaderboard")
def leaderboard(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    svc = _svc(session)
    items, total = svc.leaderboard(page, page_size)
    return ResponseSchema.pagination_response(items, total=total, page=page, page_size=page_size)


@manager_router.post("/{manager_id}/transfers")
def make_transfer(
    manager_id: int,
    body: TransferRequest,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    if user.id != manager_id and user.role != UserRole.ADMIN:
        return ResponseSchema.forbidden("Cannot transfer for another manager")

    svc = _svc(session)
    result = svc.make_transfer(manager_id, body.player_out_id, body.player_in_id, body.gw_id)
    if result == "OK":
        return ResponseSchema.success(message="Transfer completed with 4-point penalty")
    return ResponseSchema.bad_request(result)


@manager_router.post("/{manager_id}/substitute")
def substitute_player(
    manager_id: int,
    player_out_id: int,
    player_in_id: int,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    if user.id != manager_id and user.role != UserRole.ADMIN:
        return ResponseSchema.forbidden("Cannot substitute for another manager")

    svc = _svc(session)
    result = svc.substitute(manager_id, player_out_id, player_in_id)
    if result == "OK":
        return ResponseSchema.success(message="Substitution applied")
    return ResponseSchema.bad_request(result)


@manager_router.put("/{manager_id}/transfers/{transfer_id}")
def update_transfer(
    manager_id: int,
    transfer_id: int,
    body: TransferRequest,
    user: ManagerUser,
    session: Session = Depends(get_session),
):
    if user.id != manager_id and user.role != UserRole.ADMIN:
        return ResponseSchema.forbidden("Cannot modify another manager's transfer")

    svc = _svc(session)
    result = svc.update_transfer(manager_id, transfer_id, body.player_out_id, body.player_in_id)
    if result == "OK":
        return ResponseSchema.success(message="Transfer updated")
    if result == "Transfer not found":
        return ResponseSchema.not_found(result)
    return ResponseSchema.bad_request(result)


