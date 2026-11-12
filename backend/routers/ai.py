from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth.deps import get_current_user, require_role
from ..dependencies import classifier, get_ticket_service, self_help_advisor
from ..models import User
from ..schemas import (
    AIPerformanceSchema,
    AITrainResponse,
    ClassificationRequest,
    ClassificationResultSchema,
    SelfHelpRequest,
    SelfHelpResponseSchema,
)
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
def classify(payload: ClassificationRequest, ticket_service: TicketService = Depends(get_ticket_service), user: User = Depends(get_current_user)):
    prediction = classifier.predict(payload.subject, payload.description, payload.agency)
    # The low-confidence fallback returns "helpdesk-core", which is an alias, not a real team slug.
    team = ticket_service._team_by_slug(prediction.team_slug)
    agent = ticket_service._primary_agent_for_team(team.id)

    user_region = user.region or "Inconnue"
    service_concerne = _SERVICE_MAPPING.get(prediction.category, "Support logistique à qualifier")
    equipe_cible = team.slug.replace("-", " ").title()

    return ClassificationResultSchema(
        category=prediction.category,
        priority=prediction.priority,
        team_id=team.id,
        team_name=team.name,
        team_slug=team.slug,
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


@router.get("/performance", response_model=AIPerformanceSchema)
def ai_performance(ticket_service: TicketService = Depends(get_ticket_service), user=Depends(require_role({"Support_IT"}))):
    """How often agents accept the AI's suggestion as-is vs. correct it."""
    return AIPerformanceSchema(**ticket_service.ai_performance())


@router.post("/self-help", response_model=SelfHelpResponseSchema)
def self_help(payload: SelfHelpRequest, user: User = Depends(get_current_user)):
    """Offer a quick self-fix before a ticket is created, for problems simple
    enough that the person likely doesn't need IT at all."""
    article = self_help_advisor.suggest(payload.subject, payload.description)
    if not article:
        return SelfHelpResponseSchema(matched=False)
    return SelfHelpResponseSchema(matched=True, title=article.title, steps=article.steps)
