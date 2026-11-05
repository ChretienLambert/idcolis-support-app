from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..db.session import get_db
from ..models import Agent, Team
from ..schemas import AgentSchema, TeamSchema
from ..serializers import agent_schema, team_schema

router = APIRouter()


@router.get("/teams", response_model=list[TeamSchema])
def list_teams(user=Depends(get_current_user), db: Session = Depends(get_db)):
    teams = db.execute(select(Team).order_by(Team.name.asc())).scalars().all()
    return [team_schema(team) for team in teams]


@router.get("/agents", response_model=list[AgentSchema])
def list_agents(team_id: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Agent).order_by(Agent.is_primary.desc(), Agent.is_active.desc())
    if team_id:
        stmt = stmt.where(Agent.team_id == team_id)
    agents = db.execute(stmt).scalars().all()
    return [agent_schema(agent) for agent in agents]
