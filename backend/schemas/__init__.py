from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class RoleSchema(BaseModel):
    id: int
    name: str
    description: str


class TeamSchema(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    default_queue: str


class AgentSchema(BaseModel):
    id: str
    user_id: str
    user_name: str
    team_id: str
    team_name: str
    title: str
    is_primary: bool
    is_active: bool


class AuthUserSchema(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    region: str | None = None
    department: str | None = None


class AuthSessionSchema(BaseModel):
    user: AuthUserSchema
    access_token: str
    refresh_token: str
    session_id: str
    session_key: str
    access_expires_at: datetime
    refresh_expires_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr | None = None
    name: str | None = Field(default=None, min_length=2, max_length=160)
    password: str = Field(min_length=8)
    agency: Literal["Trésor Voyages", "Global Voyages"] | None = None
    station: str | None = Field(default=None, min_length=2, max_length=160)


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class RestoreSessionRequest(BaseModel):
    session_id: str
    session_key: str
    agency: Literal["Trésor Voyages", "Global Voyages"] | None = None


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
    session_id: str | None = None
    session_key: str | None = None


class TicketCommentCreate(BaseModel):
    body: str = Field(min_length=1)
    is_internal: bool = False


class TicketAssignmentCreate(BaseModel):
    to_team_id: str | None = None
    to_agent_id: str | None = None
    reason: str = ""


class TicketUpdate(BaseModel):
    subject: str | None = None
    description: str | None = None
    status: Literal["Ouvert", "En cours", "En attente", "Résolu", "Clôturé", "Intervention terrain"] | None = None
    category: str | None = None
    priority: str | None = None


class TicketCreateRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=5)
    agency: str | None = None
    site: str | None = None
    city: str | None = None
    operational_impact: Literal["Individuel", "Équipe", "Agence", "Réseau"] = "Individuel"
    field_intervention_required: bool = False


class ClassificationRequest(BaseModel):
    subject: str
    description: str
    agency: str | None = None


class TicketSummarySchema(BaseModel):
    id: str
    requester_user_id: str
    subject: str
    category: str
    priority: str | None = None
    status: str
    team_name: str
    assigned_agent_name: str | None
    requester_name: str
    requester_email: EmailStr | None = None
    agency: str | None = None
    site: str | None = None
    city: str | None = None
    field_intervention_required: bool = False
    origine_ticket: str | None = None
    created_at: datetime
    updated_at: datetime


class TicketCommentSchema(BaseModel):
    id: str
    author_user_id: str
    author_name: str
    author_role: str
    body: str
    is_internal: bool
    created_at: datetime


class TicketDetailSchema(BaseModel):
    id: str
    requester_user_id: str
    requester_name: str
    requester_email: str
    subject: str
    description: str
    agency: str | None = None
    site: str | None = None
    city: str | None = None
    operational_impact: str | None = None
    field_intervention_required: bool = False
    category: str
    priority: str | None = None
    status: str
    type_incident: str
    service_concerne: str | None = None
    origine_ticket: str | None = None
    team_id: str
    team_name: str
    assigned_agent_id: str | None
    assigned_agent_name: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    allow_user_edit: bool
    ai_model_name: str | None = None
    ai_confidence: float | None = None
    ai_team_name: str | None = None
    ai_agent_name: str | None = None
    ai_notes: str | None = None
    comments: list[TicketCommentSchema]


class InterventionCreate(BaseModel):
    agency: str | None = None
    site: str | None = None
    city: str | None = None
    contact_name: str | None = None
    diagnosis: str | None = None
    actions_performed: str | None = None
    equipment_involved: str | None = None
    materials_used: str | None = None
    tests_performed: str | None = None
    result: Literal["Brouillon", "Résolu", "Partiellement résolu", "Non résolu", "Escaladé"] = "Brouillon"
    follow_up: str | None = None
    resolution_notes: str | None = None
    technician_notes: str | None = None
    agency_comments: str | None = None


class InterventionSchema(InterventionCreate):
    id: str
    ticket_id: str
    intervention_number: str
    technician_user_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ClassificationResultSchema(BaseModel):
    category: str
    priority: str
    team_id: str
    team_name: str
    team_slug: str
    agent_id: str | None
    agent_name: str | None
    confidence: float
    model_name: str
    notes: str = ""
    origine_ticket: str | None = None
    service_concerne: str | None = None
    equipe_cible_suggeree: str | None = None


class AITrainResponse(BaseModel):
    ok: bool
    samples: int
    model_name: str


class AuditLogSchema(BaseModel):
    id: str
    actor_user_id: str | None
    entity_type: str
    entity_id: str
    action: str
    payload_json: dict[str, Any]
    created_at: datetime


class HealthSchema(BaseModel):
    ok: bool
    env: str


