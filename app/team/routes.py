from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db_models import Team
from app.utils.db import get_session
from app.utils.responses import ResponseSchema

team_router = APIRouter(prefix="/teams", tags=["Teams"])


@team_router.get("")
def list_teams(session: Session = Depends(get_session)):
	rows = session.exec(select(Team)).all()
	return ResponseSchema.success(
		data=[
			{
				"team_id": t.team_id,
				"team_name": t.team_name,
				"team_shortname": t.team_shortname,
				"team_logo_url": t.team_logo_url,
			}
			for t in rows
		]
	)
























