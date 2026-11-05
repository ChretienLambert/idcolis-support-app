from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user, require_role
from ..db.session import get_db
from ..dependencies import get_ticket_service
from ..models import AuditLog
from ..schemas import (
    AuditLogSchema,
    TicketAssignmentCreate,
    TicketCommentCreate,
    TicketCreateRequest,
    TicketDetailSchema,
    TicketSummarySchema,
    TicketUpdate,
)
from ..serializers import ticket_detail, ticket_summary
from ..services.tickets import TicketService

router = APIRouter(prefix="/tickets")


@router.get("", response_model=list[TicketSummarySchema])
def list_tickets(
    priority: str | None = None,
    status_filter: str | None = None,
    agency: str | None = None,
    ticket_service: TicketService = Depends(get_ticket_service),
    user=Depends(get_current_user),
):
    tickets = ticket_service.list_tickets(user, priority=priority, status=status_filter, agency=agency)
    return [ticket_summary(ticket) for ticket in tickets]


@router.get("/{ticket_id}", response_model=TicketDetailSchema)
def ticket_detail_view(ticket_id: str, ticket_service: TicketService = Depends(get_ticket_service), user=Depends(get_current_user)):
    try:
        ticket = ticket_service.get_ticket(ticket_id, user=user)
        return ticket_detail(ticket)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("", response_model=TicketDetailSchema)
def create_ticket(payload: TicketCreateRequest, ticket_service: TicketService = Depends(get_ticket_service), user=Depends(get_current_user)):
    if user.role.name not in {"Utilisateur", "Support_IT"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only users and support agents can create tickets.")
    try:
        metadata = payload.model_dump()
        metadata["agency"] = getattr(user, "_agency_scope", None) or metadata.get("agency")
        if not metadata["agency"]:
            raise HTTPException(status_code=400, detail="An agency must be selected before creating a ticket.")
        ticket = ticket_service.create_ticket(user.id, payload.subject, payload.description, created_by_user_id=user.id, metadata=metadata)
        return ticket_detail(ticket_service.get_ticket(ticket.id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{ticket_id}", response_model=TicketDetailSchema)
def update_ticket(ticket_id: str, payload: TicketUpdate, ticket_service: TicketService = Depends(get_ticket_service), user=Depends(get_current_user)):
    try:
        updated = ticket_service.update_ticket(ticket_id, payload.model_dump(exclude_unset=True), actor_user_id=user.id, actor_role=user.role.name)
        return ticket_detail(updated)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{ticket_id}/comments", response_model=TicketDetailSchema)
def add_comment(ticket_id: str, payload: TicketCommentCreate, ticket_service: TicketService = Depends(get_ticket_service), user=Depends(get_current_user)):
    try:
        ticket_service.add_comment(ticket_id, user.id, user.role.name, payload.body, payload.is_internal)
        return ticket_detail(ticket_service.get_ticket(ticket_id))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{ticket_id}/status", response_model=TicketDetailSchema)
@router.patch("/{ticket_id}/status", response_model=TicketDetailSchema)
def change_status(ticket_id: str, payload: TicketUpdate, ticket_service: TicketService = Depends(get_ticket_service), user=Depends(get_current_user)):
    if user.role.name != "Support_IT":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only support agents can change status.")
    if not payload.status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status is required.")
    try:
        ticket_service.change_status(ticket_id, payload.status, actor_user_id=user.id)
        return ticket_detail(ticket_service.get_ticket(ticket_id))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{ticket_id}/approve", response_model=TicketDetailSchema)
def approve_ai_suggestions(
    ticket_id: str,
    category: str,
    priority: str,
    team_slug: str,
    service_concerne: str | None = None,
    corrected: bool = False,
    ticket_service: TicketService = Depends(get_ticket_service),
    user=Depends(get_current_user),
):
    if user.role.name != "Support_IT":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only support agents can approve AI suggestions.")
    try:
        ticket = ticket_service.approve_ai_suggestions(ticket_id, user.id, category, priority, team_slug, corrected, service_concerne)
        return ticket_detail(ticket)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/{ticket_id}/assign", response_model=TicketDetailSchema)
def assign_ticket(ticket_id: str, payload: TicketAssignmentCreate, ticket_service: TicketService = Depends(get_ticket_service), user=Depends(get_current_user)):
    if user.role.name != "Support_IT":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only support agents can reassign tickets.")
    try:
        updated = ticket_service.assign_ticket(ticket_id, to_team_id=payload.to_team_id, to_agent_id=payload.to_agent_id, reason=payload.reason, actor_user_id=user.id)
        return ticket_detail(updated)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{ticket_id}/audit", response_model=list[AuditLogSchema])
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
