from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import event
from sqlmodel import Session, select

from app.db_models import ManagersSquad, Player, PlayerStat
from app.scoring.service import ScoringService


def _collect_player_stat_changes(session: Session) -> dict[tuple[int, int], PlayerStat]:
    """Collect PlayerStat instances that are new/dirty, keyed by (player_id, gw_id)."""
    changed: dict[tuple[int, int], PlayerStat] = {}

    def _iter_objects(items: Iterable[object]) -> Iterable[PlayerStat]:
        for obj in items:
            if isinstance(obj, PlayerStat):
                yield obj

    for ps in _iter_objects(session.new):
        changed[(ps.player_id, ps.gw_id)] = ps
    for ps in _iter_objects(session.dirty):
        # Only consider if any relevant fields changed or simply recompute
        changed[(ps.player_id, ps.gw_id)] = ps

    return changed


@event.listens_for(Session, "before_flush")
def player_stats_before_flush(session: Session, flush_context, instances) -> None:  # type: ignore[no-untyped-def]
    """Recalculate PlayerStat.total_points before flushing to DB.

    Ensures total_points is always consistent whenever stats are inserted/updated.
    """
    scoring = ScoringService(session)

    changed_map = _collect_player_stat_changes(session)
    if not changed_map:
        return

    # Store changed pairs for later manager updates
    pending = session.info.setdefault("_updated_player_stats", set())
    pending.update(changed_map.keys())

    # Recalculate for all PlayerStat instances currently pending in the session
    for (player_id, _gw_id), player_stat in changed_map.items():
        player = session.get(Player, player_id)
        if not player:
            continue

        player_stat.total_points = scoring.calculate_player_points(player_stat, player)
        session.add(player_stat)


@event.listens_for(Session, "after_commit")
def update_managers_after_commit(session: Session) -> None:  # type: ignore[no-untyped-def]
    """After commit of PlayerStat changes, update affected managers' gameweek points."""
    changed: set[tuple[int, int]] = session.info.get("_updated_player_stats", set())
    if not changed or session.info.get("_in_manager_update"):
        session.info.pop("_updated_player_stats", None)
        return

    session.info["_in_manager_update"] = True
    try:
        scoring = ScoringService(session)
        for (player_id, gw_id) in changed:
            manager_ids = session.exec(
                select(ManagersSquad.manager_id)
                .where(ManagersSquad.player_id == player_id)
                .where(ManagersSquad.gw_id == gw_id)
            ).all()
            for manager_id in manager_ids:
                scoring.update_manager_gameweek_points(manager_id, gw_id)
        session.info.pop("_updated_player_stats", None)
    finally:
        session.info.pop("_in_manager_update", None)


