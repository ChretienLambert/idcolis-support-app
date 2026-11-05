from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user, require_role
from ..config import settings
from ..db.session import get_db
from ..models import Intervention, InterventionAttachment, Ticket, utcnow
from ..schemas import InterventionCreate, InterventionReview, InterventionSchema, TicketDetailSchema
from ..serializers import ticket_detail

router = APIRouter()


def _check_agency_scope(user, ticket: Ticket) -> None:
    agency_scope = getattr(user, "_agency_scope", None)
    if agency_scope and ticket.agency != agency_scope:
        raise HTTPException(status_code=403, detail="This ticket belongs to another agency.")


@router.post("/tickets/{ticket_id}/interventions", response_model=InterventionSchema)
def create_intervention(ticket_id: str, payload: InterventionCreate, db: Session = Depends(get_db), user=Depends(require_role({"Support_IT"}))):
    """Create a structured field intervention report for a ticket."""
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    _check_agency_scope(user, ticket)
    count = db.query(Intervention).count() + 1
    intervention = Intervention(ticket_id=ticket_id, intervention_number=f"INT-{utcnow().year}-{count:05d}", technician_user_id=user.id, **payload.model_dump())
    ticket.field_intervention_required = True
    # Every new intervention starts in progress. Completion is decided only by
    # the regulator and requester validation chain.
    ticket.status = "En cours"
    db.add(intervention)
    db.commit()
    db.refresh(intervention)
    return intervention


@router.get("/tickets/{ticket_id}/interventions", response_model=list[InterventionSchema])
def list_interventions(ticket_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    _check_agency_scope(user, ticket)
    return list(db.execute(select(Intervention).where(Intervention.ticket_id == ticket_id).order_by(Intervention.created_at.asc())).scalars().all())


@router.patch("/interventions/{intervention_id}", response_model=InterventionSchema)
def update_intervention(intervention_id: str, payload: InterventionCreate, db: Session = Depends(get_db), user=Depends(require_role({"Support_IT"}))):
    intervention = db.get(Intervention, intervention_id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    _check_agency_scope(user, intervention.ticket)
    if intervention.review_status == "Approuvée" and intervention.user_validated_at:
        raise HTTPException(status_code=409, detail="This intervention is closed and cannot be modified.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(intervention, key, value)
    intervention.updated_at = utcnow()
    # A corrected report must return to the regulator for a fresh decision.
    intervention.review_status = "En attente de validation"
    intervention.review_feedback = None
    intervention.reviewed_by_user_id = None
    intervention.reviewed_at = None
    intervention.user_validated_at = None
    if intervention.result in {"Résolu", "Suspendu"}:
        intervention.ticket.status = "En attente de validation"
        intervention.ticket.resolved_at = utcnow() if intervention.result == "Résolu" else None
    db.commit()
    db.refresh(intervention)
    return intervention


@router.post("/interventions/{intervention_id}/review", response_model=InterventionSchema)
def review_intervention(intervention_id: str, payload: InterventionReview, db: Session = Depends(get_db), user=Depends(require_role({"Régulateur_Agence"}))):
    """Approve an intervention or return it to IT with correction feedback."""
    intervention = db.get(Intervention, intervention_id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    _check_agency_scope(user, intervention.ticket)
    latest = db.execute(
        select(Intervention).where(Intervention.ticket_id == intervention.ticket_id).order_by(Intervention.created_at.desc())
    ).scalars().first()
    if not latest or latest.id != intervention.id:
        raise HTTPException(status_code=409, detail="Only the latest intervention iteration can be reviewed.")
    if payload.decision == "correction_required" and not payload.feedback.strip():
        raise HTTPException(status_code=400, detail="Correction feedback is required.")
    intervention.review_status = "Approuvée" if payload.decision == "approved" else "À corriger"
    intervention.review_feedback = payload.feedback.strip() or None
    intervention.reviewed_by_user_id = user.id
    intervention.reviewed_at = utcnow()
    intervention.ticket.status = "En attente de validation" if payload.decision == "approved" else "À corriger"
    db.commit()
    db.refresh(intervention)
    return intervention


@router.post("/tickets/{ticket_id}/validate", response_model=TicketDetailSchema)
def validate_ticket(ticket_id: str, db: Session = Depends(get_db), user=Depends(require_role({"Utilisateur"}))):
    """Let the requester confirm the regulator-approved resolution."""
    ticket = db.get(Ticket, ticket_id)
    if not ticket or ticket.requester_user_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    latest = db.execute(select(Intervention).where(Intervention.ticket_id == ticket_id).order_by(Intervention.created_at.desc())).scalars().first()
    if not latest or latest.review_status != "Approuvée":
        raise HTTPException(status_code=400, detail="The ticket has not been approved by the regulator.")
    latest.user_validated_at = utcnow()
    ticket.status = "Résolu"
    ticket.resolved_at = utcnow()
    db.commit()
    db.refresh(ticket)
    return ticket_detail(ticket)


@router.post("/interventions/{intervention_id}/attachments")
def upload_intervention_attachment(intervention_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(require_role({"Support_IT"}))):
    """Persist a validated field-evidence attachment for an intervention."""
    intervention = db.get(Intervention, intervention_id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    _check_agency_scope(user, intervention.ticket)
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
