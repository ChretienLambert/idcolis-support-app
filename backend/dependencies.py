from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from .ai.model import TicketRoutingModel
from .db.session import get_db
from .services.tickets import TicketService

# Shared across every router: the AI routing model is process-wide state, not
# per-request, so it lives here instead of inside backend.app.
classifier = TicketRoutingModel()


def get_ticket_service(db: Session = Depends(get_db)) -> TicketService:
    return TicketService(db, classifier)
