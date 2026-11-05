from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..db.session import get_db
from ..models import AgencyStation, Role, User, UserAgency

router = APIRouter()


@router.get("/directory")
def agency_directory(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Return only the stations belonging to the agency bound to the session."""
    agency = getattr(user, "_agency_scope", None)
    if not agency:
        raise HTTPException(status_code=400, detail="No agency is bound to this session.")
    stations = db.execute(select(AgencyStation).where(AgencyStation.agency == agency).order_by(AgencyStation.city, AgencyStation.name)).scalars().all()
    assignments = db.execute(select(UserAgency, User).join(User, User.id == UserAgency.user_id).where(UserAgency.agency == agency)).all()
    by_station = {}
    for assignment, person in assignments:
        by_station.setdefault(assignment.station, []).append({"name": assignment.post, "assigned_user": person.full_name, "email": person.email, "user_id": person.id})
    return [{"id": s.id, "agency": s.agency, "name": s.name, "city": s.city, "address": s.address, "phone": s.phone, "posts": by_station.get(s.name, s.posts_json)} for s in stations]


@router.get("/public/agents")
def public_agents(agency: str, station: str, db: Session = Depends(get_db)):
    """Return the station's agents plus the agency regulator for login."""
    rows = db.execute(
        select(UserAgency, User)
        .join(User, User.id == UserAgency.user_id)
        .join(Role, User.role_id == Role.id)
        .where(UserAgency.agency == agency)
        .order_by(UserAgency.station, User.full_name)
    ).all()
    result = []
    for assignment, user in rows:
        if assignment.station == station or user.role.name == "Régulateur_Agence":
            result.append({"name": user.full_name, "post": assignment.post or "Régulateur agence", "role": user.role.name})
    return result
