from __future__ import annotations

import base64
from pathlib import Path
import shutil
import uuid
import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .ai.model import TicketRoutingModel
from .auth.deps import get_auth_service, get_current_user, require_role
from .config import settings
from .db.base import Base
from .db.session import SessionLocal, engine, get_db
from .logging import build_logger
from .models import AgencyStation, Agent, AuditLog, Intervention, InterventionAttachment, Role, Team, Ticket, User, UserAgency, utcnow
from .schemas import (
    AITrainResponse,
    AuditLogSchema,
    AuthSessionSchema,
    AuthUserSchema,
    AgentSchema,
    ClassificationResultSchema,
    ClassificationRequest,
    HealthSchema,
    LoginRequest,
    LogoutRequest,
    RestoreSessionRequest,
    TicketCommentCreate,
    TicketDetailSchema,
    TicketAssignmentCreate,
    TicketCreateRequest,
    TicketSummarySchema,
    TicketUpdate,
    TeamSchema,
    InterventionCreate,
    InterventionSchema,
)
from .seed.demo import reference_training_rows, seed_demo_data, ensure_demo_data
from .services.tickets import TicketService


app = FastAPI(title=settings.app_name, version="0.1.0")
allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_login_attempts: dict[str, deque[float]] = defaultdict(deque)
_LOGIN_WINDOW_SECONDS = 60
_LOGIN_LIMIT = 10


@app.middleware("http")
async def login_rate_limit(request: Request, call_next):
    """Limit repeated login attempts per client IP without affecting normal API use."""
    if request.scope["path"].rstrip("/") == "/auth/login" and request.method.upper() == "POST":
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        attempts = _login_attempts[client_ip]
        while attempts and now - attempts[0] > _LOGIN_WINDOW_SECONDS:
            attempts.popleft()
        if len(attempts) >= _LOGIN_LIMIT:
            return JSONResponse(status_code=429, content={"detail": "Too many login attempts. Please wait one minute."})
        attempts.append(now)
    return await call_next(request)


@app.middleware("http")
async def api_prefix_compatibility(request: Request, call_next):
    """Expose the same routes under /api without breaking the existing portal client."""
    if request.scope["path"].startswith("/api/"):
        request.scope["path"] = request.scope["path"][4:]
    return await call_next(request)

Base.metadata.create_all(bind=engine)


classifier = TicketRoutingModel()
auth_logger = build_logger("ID Colis.auth", "auth.log")


def get_ticket_service(db: Session = Depends(get_db)) -> TicketService:
    return TicketService(db, classifier)


def _user_schema(user: User) -> AuthUserSchema:
    return AuthUserSchema(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name,
        is_active=user.is_active,
        region=user.region,
        department=user.department
    )


def _ticket_summary(ticket: Ticket) -> TicketSummarySchema:
    team_name = ticket.team.name if ticket.team else ""
    assigned_agent_name = ticket.assigned_agent.user.full_name if ticket.assigned_agent and ticket.assigned_agent.user else None
    return TicketSummarySchema(
        id=ticket.id,
        requester_user_id=ticket.requester_user_id,
        subject=ticket.subject,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        team_name=team_name,
        assigned_agent_name=assigned_agent_name,
        requester_name=ticket.requester.full_name if ticket.requester else "",
        requester_email=ticket.requester.email if ticket.requester else None,
        agency=ticket.agency,
        site=ticket.site,
        city=ticket.city,
        field_intervention_required=ticket.field_intervention_required,
        origine_ticket=ticket.requester.region if ticket.requester else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def _ticket_detail(ticket: Ticket) -> TicketDetailSchema:
    team_name = ticket.team.name if ticket.team else ""
    assigned_agent_name = ticket.assigned_agent.user.full_name if ticket.assigned_agent and ticket.assigned_agent.user else None
    latest_prediction = None
    if ticket.predictions:
        latest_prediction = sorted(ticket.predictions, key=lambda item: item.created_at)[-1]
    return TicketDetailSchema(
        id=ticket.id,
        requester_user_id=ticket.requester_user_id,
        requester_name=ticket.requester.full_name if ticket.requester else "",
        requester_email=ticket.requester.email if ticket.requester else "",
        subject=ticket.subject,
        description=ticket.description,
        agency=ticket.agency,
        site=ticket.site,
        city=ticket.city,
        operational_impact=ticket.operational_impact,
        field_intervention_required=ticket.field_intervention_required,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        type_incident="",
        service_concerne=ticket.service_concerne,
        origine_ticket=ticket.requester.region if ticket.requester else None,
        team_id=ticket.team_id,
        team_name=team_name,
        assigned_agent_id=ticket.assigned_agent_id,
        assigned_agent_name=assigned_agent_name,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        allow_user_edit=False,
        ai_model_name=latest_prediction.model_name if latest_prediction else None,
        ai_confidence=latest_prediction.confidence if latest_prediction else None,
        ai_team_name=team_name if latest_prediction else None,
        ai_agent_name=assigned_agent_name if latest_prediction else None,
        ai_notes=latest_prediction.features_json.get("notes") if latest_prediction else None,
        comments=[
            {
                "id": comment.id,
                "author_user_id": comment.author_user_id,
                "author_name": comment.author.full_name if comment.author else "",
                "author_role": comment.author_role,
                "body": comment.body,
                "is_internal": comment.is_internal,
                "created_at": comment.created_at,
            }
            for comment in ticket.comments
        ],
    )


def _team_schema(team: Team) -> TeamSchema:
    return TeamSchema(id=team.id, name=team.name, slug=team.slug, description=team.description, default_queue=team.default_queue)


def _agent_schema(agent: Agent) -> AgentSchema:
    return AgentSchema(
        id=agent.id,
        user_id=agent.user_id,
        user_name=agent.user.full_name if agent.user else "",
        team_id=agent.team_id,
        team_name=agent.team.name if agent.team else "",
        title=agent.title,
        is_primary=agent.is_primary,
        is_active=agent.is_active,
    )


@app.get("/directory")
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


@app.get("/public/agents")
def public_agents(agency: str, station: str, db: Session = Depends(get_db)):
    """Return names only for the two demo accounts assigned to a login location."""
    rows = db.execute(select(UserAgency, User).join(User, User.id == UserAgency.user_id).where(UserAgency.agency == agency, UserAgency.station == station)).all()
    return [{"name": user.full_name, "post": assignment.post} for assignment, user in rows]


@app.on_event("startup")
def startup() -> None:
    with SessionLocal() as db:
        _seed_directory(db)
        _seed_user_agencies(db)
        _backfill_demo_ticket_tenants(db)
        # Check if we already have users. If not, seed essential data.
        user_count = db.execute(select(User)).scalars().first()
        if not user_count:
            ensure_demo_data(db)

        ts = TicketService(db, classifier)
        training_rows = ts.get_training_data()
        if training_rows:
            classifier.train(training_rows)
        else:
            classifier.load()


def _seed_directory(db: Session) -> None:
    """Seed the initial agency/station directory without mixing tenants."""
    rows = [
        ("Global Voyages", "Bafoussam >> Douala", "Bafoussam", "Quartier Ndiengso", "690694318"),
        ("Global Voyages", "Bafoussam >> Yaoundé", "Bafoussam", "Quartier Ndiengso", "690694318"),
        ("Global Voyages", "Biyem-Assi", "Yaoundé", "Carrefour Biyem-Assi", "656674860"),
        ("Global Voyages", "DLA-Bépanda", "Douala", "Quartier Bépanda", "658595989"),
        ("Global Voyages", "DLA-Brazzaville", "Douala", "Quartier Brazzaville", "690643275"),
        ("Global Voyages", "DLA-Mboppi", "Douala", "Quartier Mboppi", "690674364"),
        ("Global Voyages", "DLA-Village", "Douala", "Entrée-billes", "690029529"),
        ("Global Voyages", "Douala Akwa", "Douala", "Akwa", "692339031"),
        ("Trésor Voyages", "Bafoussam", "Bafoussam", "Quartier Ndiengso", "691832408"),
        ("Trésor Voyages", "Baneghang", "Baneghang", "Baneghang", "692105461"),
        ("Trésor Voyages", "DLA-Bépanda", "Douala", "Quartier Bépanda", "691832671"),
        ("Trésor Voyages", "DLA-Bonabéri", "Douala", "Quartier Bonabéri", "691832670"),
        ("Trésor Voyages", "DLA-Brazzaville", "Douala", "Quartier Brazzaville", "691832672"),
        ("Trésor Voyages", "DLA-Village", "Douala", "Quartier Village", "695612260"),
        ("Trésor Voyages", "Dschang", "Dschang", "Entrée de la ville", "691832148"),
        ("Trésor Voyages", "Mvan 2", "Yaoundé", "Yaoundé", "690529802"),
    ]
    desired = {(agency, name) for agency, name, *_ in rows}
    for station in db.execute(select(AgencyStation)).scalars().all():
        if (station.agency, station.name) not in desired:
            db.delete(station)
    existing = {(s.agency, s.name) for s in db.execute(select(AgencyStation)).scalars().all()}
    for agency, name, city, address, phone in rows:
        if (agency, name) not in existing:
            db.add(AgencyStation(agency=agency, name=name, city=city, address=address, phone=phone, posts_json=[{"name": "Vente / dépôt", "assigned_user": None}, {"name": "Expédition / retrait", "assigned_user": None}]))
    db.commit()


def _backfill_demo_ticket_tenants(db: Session) -> None:
    """Keep legacy demo tickets visible in exactly one tenant queue."""
    unassigned = db.execute(select(Ticket).where(Ticket.agency.is_(None)).order_by(Ticket.created_at.asc())).scalars().all()
    for index, ticket in enumerate(unassigned):
        ticket.agency = "Global Voyages" if index % 2 == 0 else "Trésor Voyages"
    if unassigned:
        db.commit()


def _seed_user_agencies(db: Session) -> None:
    """Ensure every station has two exclusive demo workstation users."""
    from .auth.service import hash_password

    stations = {agency: db.execute(select(AgencyStation).where(AgencyStation.agency == agency).order_by(AgencyStation.name)).scalars().all() for agency in ("Global Voyages", "Trésor Voyages")}
    users = db.execute(select(User).join(Role).where(Role.name == "Utilisateur").order_by(User.email)).scalars().all()
    role = db.execute(select(Role).where(Role.name == "Utilisateur")).scalar_one()
    required = sum(len(items) * 2 for items in stations.values())
    demo_names = ["Aline Kamga", "Boris Tchana", "Clarisse Ndomo", "Didier Foka", "Estelle Mvondo", "Franck Tamba", "Grace Ngu", "Hervé Mballa", "Irene Njoya", "Junior Ebong", "Kevin Meka", "Laure Mbianda", "Mireille Nono", "Nadia Fotso", "Olivier Toko", "Prisca Muna", "Rosine Abena", "Serge Biloa", "Thérèse Etoa", "Ulrich Nsame", "Valérie Kenne", "Wilfried Momo"]
    for index in range(len(users), required):
        user = User(email=f"station.user{index + 1}@idcolis.cm", full_name=demo_names[index - 10] if index - 10 < len(demo_names) else f"Agent agence {index + 1}", password_hash=hash_password("IDColis2024!"), role_id=role.id, is_active=True, region="Littoral", department="Opérations")
        db.add(user)
        db.flush()
        users.append(user)
    for index, user in enumerate(users):
        if user.full_name.startswith("Utilisateur station") and index - 10 < len(demo_names):
            user.full_name = demo_names[index - 10]
    for assignment in db.execute(select(UserAgency)).scalars().all():
        db.delete(assignment)
    db.flush()
    index = 0
    for agency, agency_stations in stations.items():
        for station in agency_stations:
            for post in ("Vente / dépôt", "Expédition / retrait"):
                db.add(UserAgency(user_id=users[index].id, agency=agency, station=station.name, post=post))
                index += 1
    db.commit()


@app.get("/health", response_model=HealthSchema)
def health():
    return HealthSchema(ok=True, env=settings.env)


@app.post("/auth/login", response_model=AuthSessionSchema)
def login(payload: LoginRequest, service=Depends(get_auth_service)):
    try:
        session = service.sign_in(payload.email, payload.password, payload.agency, payload.station, payload.name)
        auth_logger.info("login_attempt email=%s result=success role=%s", payload.email, session.user.role)
        return session
    except Exception as exc:
        auth_logger.info("login_attempt email=%s result=failure reason=%s", payload.email, type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.") from exc


@app.post("/auth/restore", response_model=AuthSessionSchema)
def restore(payload: RestoreSessionRequest, service=Depends(get_auth_service)):
    try:
        return service.restore(payload.session_id, payload.session_key, payload.agency)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@app.post("/auth/logout")
def logout(payload: LogoutRequest, service=Depends(get_auth_service)):
    service.revoke(payload.session_id, payload.session_key)
    return {"ok": True}


@app.get("/auth/me", response_model=AuthUserSchema)
def me(user=Depends(get_current_user)):
    return _user_schema(user)


@app.get("/teams", response_model=list[TeamSchema])
def list_teams(user=Depends(get_current_user), db: Session = Depends(get_db)):
    teams = db.execute(select(Team).order_by(Team.name.asc())).scalars().all()
    return [_team_schema(team) for team in teams]


@app.get("/agents", response_model=list[AgentSchema])
def list_agents(team_id: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Agent).order_by(Agent.is_primary.desc(), Agent.is_active.desc())
    if team_id:
        stmt = stmt.where(Agent.team_id == team_id)
    agents = db.execute(stmt).scalars().all()
    return [_agent_schema(agent) for agent in agents]


@app.get("/tickets", response_model=list[TicketSummarySchema])
def list_tickets(
    priority: str | None = None,
    status_filter: str | None = None,
    agency: str | None = None,
    db: Session = Depends(get_db),
    ticket_service: TicketService = Depends(get_ticket_service),
    user=Depends(get_current_user),
):
    tickets = ticket_service.list_tickets(user, priority=priority, status=status_filter, agency=agency)
    return [_ticket_summary(ticket) for ticket in tickets]


@app.get("/tickets/{ticket_id}", response_model=TicketDetailSchema)
def ticket_detail(ticket_id: str, ticket_service: TicketService = Depends(get_ticket_service), user=Depends(get_current_user)):
    try:
        ticket = ticket_service.get_ticket(ticket_id, user=user)
        return _ticket_detail(ticket)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post("/tickets", response_model=TicketDetailSchema)
def create_ticket(payload: TicketCreateRequest, ticket_service: TicketService = Depends(get_ticket_service), user=Depends(get_current_user)):
    if user.role.name not in {"Utilisateur", "Support_IT"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only users and support agents can create tickets.")
    try:
        metadata = payload.model_dump()
        metadata["agency"] = getattr(user, "_agency_scope", None) or metadata.get("agency")
        if not metadata["agency"]:
            raise HTTPException(status_code=400, detail="An agency must be selected before creating a ticket.")
        ticket = ticket_service.create_ticket(user.id, payload.subject, payload.description, created_by_user_id=user.id, metadata=metadata)
        return _ticket_detail(ticket_service.get_ticket(ticket.id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/tickets/{ticket_id}/interventions", response_model=InterventionSchema)
def create_intervention(ticket_id: str, payload: InterventionCreate, db: Session = Depends(get_db), user=Depends(require_role({"Support_IT"}))):
    """Create a structured field intervention report for a ticket."""
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    count = db.query(Intervention).count() + 1
    intervention = Intervention(ticket_id=ticket_id, intervention_number=f"INT-{utcnow().year}-{count:05d}", technician_user_id=user.id, **payload.model_dump())
    ticket.field_intervention_required = True
    ticket.status = "Intervention terrain"
    db.add(intervention)
    db.commit()
    db.refresh(intervention)
    return intervention


@app.get("/tickets/{ticket_id}/interventions", response_model=list[InterventionSchema])
def list_interventions(ticket_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return list(db.execute(select(Intervention).where(Intervention.ticket_id == ticket_id).order_by(Intervention.created_at.desc())).scalars().all())


@app.patch("/interventions/{intervention_id}", response_model=InterventionSchema)
def update_intervention(intervention_id: str, payload: InterventionCreate, db: Session = Depends(get_db), user=Depends(require_role({"Support_IT"}))):
    intervention = db.get(Intervention, intervention_id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(intervention, key, value)
    intervention.updated_at = utcnow()
    if intervention.result in {"Résolu", "Partiellement résolu", "Non résolu", "Escaladé"}:
        intervention.ticket.status = "Résolu" if intervention.result == "Résolu" else "En cours"
        intervention.ticket.resolved_at = utcnow() if intervention.result == "Résolu" else None
    db.commit()
    db.refresh(intervention)
    return intervention


@app.post("/interventions/{intervention_id}/attachments")
def upload_intervention_attachment(intervention_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(require_role({"Support_IT"}))):
    """Persist a validated field-evidence attachment for an intervention."""
    intervention = db.get(Intervention, intervention_id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    allowed = {"image/jpeg", "image/png", "application/pdf", "text/plain"}
    original_name = Path(file.filename or "attachment").name
    if file.content_type not in allowed or original_name in {"", ".", ".."}:
        raise HTTPException(status_code=415, detail="Unsupported attachment type")
    data = file.file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Attachment exceeds 10 MB")
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    signatures = {
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "application/pdf": data.startswith(b"%PDF"),
        "text/plain": True,
    }
    if not signatures.get(file.content_type, False):
        raise HTTPException(status_code=415, detail="File content does not match its declared type")
    stored = f"{uuid.uuid4().hex}_{original_name}"
    target = upload_dir / stored
    target.write_bytes(data)
    attachment = InterventionAttachment(intervention_id=intervention_id, original_filename=original_name, stored_filename=stored, content_type=file.content_type or "application/octet-stream", size_bytes=len(data), uploaded_by_user_id=user.id)
    db.add(attachment)
    db.commit()
    return {"id": attachment.id, "filename": attachment.original_filename, "size_bytes": attachment.size_bytes}


@app.patch("/tickets/{ticket_id}", response_model=TicketDetailSchema)
def update_ticket(ticket_id: str, payload: TicketUpdate, ticket_service: TicketService = Depends(get_ticket_service), user=Depends(get_current_user)):
    try:
        updated = ticket_service.update_ticket(ticket_id, payload.model_dump(exclude_unset=True), actor_user_id=user.id, actor_role=user.role.name)
        return _ticket_detail(updated)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/tickets/{ticket_id}/comments", response_model=TicketDetailSchema)
def add_comment(ticket_id: str, payload: TicketCommentCreate, ticket_service: TicketService = Depends(get_ticket_service), user=Depends(get_current_user)):
    try:
        ticket_service.add_comment(ticket_id, user.id, user.role.name, payload.body, payload.is_internal)
        return _ticket_detail(ticket_service.get_ticket(ticket_id))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/tickets/{ticket_id}/status", response_model=TicketDetailSchema)
@app.patch("/tickets/{ticket_id}/status", response_model=TicketDetailSchema)
def change_status(ticket_id: str, payload: TicketUpdate, ticket_service: TicketService = Depends(get_ticket_service), user=Depends(get_current_user)):
    if user.role.name != "Support_IT":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only support agents can change status.")
    if not payload.status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status is required.")
    try:
        ticket_service.change_status(ticket_id, payload.status, actor_user_id=user.id)
        return _ticket_detail(ticket_service.get_ticket(ticket_id))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/tickets/{ticket_id}/approve", response_model=TicketDetailSchema)
def approve_ai_suggestions(
    ticket_id: str,
    category: str,
    priority: str,
    team_slug: str,
    service_concerne: str | None = None,
    corrected: bool = False,
    ticket_service: TicketService = Depends(get_ticket_service),
    user=Depends(get_current_user)
):
    if user.role.name != "Support_IT":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only support agents can approve AI suggestions.")
    try:
        ticket = ticket_service.approve_ai_suggestions(ticket_id, user.id, category, priority, team_slug, corrected, service_concerne)
        return _ticket_detail(ticket)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@app.post("/tickets/{ticket_id}/assign", response_model=TicketDetailSchema)
def assign_ticket(ticket_id: str, payload: TicketAssignmentCreate, ticket_service: TicketService = Depends(get_ticket_service), user=Depends(get_current_user)):
    if user.role.name != "Support_IT":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only support agents can reassign tickets.")
    try:
        updated = ticket_service.assign_ticket(ticket_id, to_team_id=payload.to_team_id, to_agent_id=payload.to_agent_id, reason=payload.reason, actor_user_id=user.id)
        return _ticket_detail(updated)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/ai/classify", response_model=ClassificationResultSchema)
def classify(payload: ClassificationRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    prediction = classifier.predict(payload.subject, payload.description, payload.agency)
    team = db.execute(select(Team).where(Team.slug == prediction.team_slug)).scalar_one()
    agent = db.execute(select(Agent).where(Agent.team_id == team.id, Agent.is_primary.is_(True))).scalar_one_or_none()

    # Enhanced geographic redirection logic
    user_region = user.region or "Inconnu"
    service_mapping = {
        "Outlook": "Support IT - Messagerie",
        "Réseau": "Infrastructure & Connectivité",
        "Matériel": "Support Poste de Travail",
        "Logiciels": "Support Applicatif"
    }
    service_concerne = service_mapping.get(prediction.category, "Support IT Général")

    # Logic for suggested team based on region
    if user_region in ["Centre", "Littoral"]:
        equipe_cible = f"Support Central - {user_region}"
    else:
        equipe_cible = f"Support Local - Région de l'{user_region}" if user_region != "Inconnu" else "Support Central"

    return ClassificationResultSchema(
        category=prediction.category,
        priority=prediction.priority,
        team_id=team.id,
        team_name=team.name,
        team_slug=prediction.team_slug,
        agent_id=agent.id if agent else None,
        agent_name=agent.user.full_name if agent and agent.user else None,
        confidence=prediction.confidence,
        model_name=classifier.model_name,
        notes=prediction.notes,
        origine_ticket=user_region,
        service_concerne=service_concerne,
        equipe_cible_suggeree=equipe_cible
    )


@app.post("/ai/train", response_model=AITrainResponse)
def train_ai(db: Session = Depends(get_db), ticket_service: TicketService = Depends(get_ticket_service), user=Depends(require_role({"Support_IT"}))):
    training_rows = ticket_service.get_training_data()
    samples = classifier.train(training_rows)
    return AITrainResponse(ok=True, samples=samples, model_name=classifier.model_name)


@app.get("/tickets/{ticket_id}/audit", response_model=list[AuditLogSchema])
def get_ticket_audit_logs(ticket_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role.name != "Support_IT":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only support agents can view audit logs.")
    logs = db.execute(select(AuditLog).where(AuditLog.entity_id == ticket_id).order_by(AuditLog.created_at.desc())).scalars().all()
    return [
        AuditLogSchema(
            id=log.id,
            actor_user_id=log.actor_user_id,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            action=log.action,
            payload_json=log.payload_json,
            created_at=log.created_at,
        )
        for log in logs
    ]


