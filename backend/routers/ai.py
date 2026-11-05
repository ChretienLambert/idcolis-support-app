from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user, require_role
from ..db.session import get_db
from ..dependencies import classifier, get_ticket_service
from ..models import Agent, Team, User
from ..schemas import AITrainResponse, ClassificationRequest, ClassificationResultSchema
from ..services.tickets import TicketService

router = APIRouter(prefix="/ai")

# Keep the explanation aligned with the logistics support domain.
_SERVICE_MAPPING = {
    "Fleet / Driver App": "Application chauffeur et flotte",
    "Scanning / Hardware": "Scannage et matériel",
    "Waybill / Manifest Sync": "Waybill, manifeste et synchronisation",
    "Account / Authentication": "Comptes et authentification",
    "Network / Connectivity": "Réseau et connectivité",
    "ID Colis Application": "Application ID Colis",
    "Data / Reporting": "Données et rapports",
    "Autres": "Support logistique à qualifier",
}


@router.post("/classify", response_model=ClassificationResultSchema)
def classify(payload: ClassificationRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    prediction = classifier.predict(payload.subject, payload.description, payload.agency)
    team = db.execute(select(Team).where(Team.slug == prediction.team_slug)).scalar_one()
    agent = db.execute(select(Agent).where(Agent.team_id == team.id, Agent.is_primary.is_(True))).scalar_one_or_none()

    user_region = user.region or "Inconnue"
    service_concerne = _SERVICE_MAPPING.get(prediction.category, "Support logistique à qualifier")
    equipe_cible = prediction.team_slug.replace("-", " ").title()

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
        equipe_cible_suggeree=equipe_cible,
    )


@router.post("/train", response_model=AITrainResponse)
def train_ai(ticket_service: TicketService = Depends(get_ticket_service), user=Depends(require_role({"Support_IT"}))):
    training_rows = ticket_service.get_training_data()
    samples = classifier.train(training_rows)
    return AITrainResponse(ok=True, samples=samples, model_name=classifier.model_name)
