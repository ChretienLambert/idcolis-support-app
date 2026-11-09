from __future__ import annotations

from .models import Agent, Intervention, Team, Ticket, User
from .schemas import AgentSchema, AuthUserSchema, InterventionSchema, TeamSchema, TicketDetailSchema, TicketSummarySchema


def user_schema(user: User) -> AuthUserSchema:
    return AuthUserSchema(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name,
        is_active=user.is_active,
        region=user.region,
        department=user.department,
    )


def ticket_summary(ticket: Ticket) -> TicketSummarySchema:
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


def ticket_detail(ticket: Ticket) -> TicketDetailSchema:
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


def intervention_schema(intervention: Intervention) -> InterventionSchema:
    return InterventionSchema(
        id=intervention.id,
        ticket_id=intervention.ticket_id,
        intervention_number=intervention.intervention_number,
        agency=intervention.agency,
        site=intervention.site,
        city=intervention.city,
        started_at=intervention.started_at,
        contact_name=intervention.contact_name,
        diagnosis=intervention.diagnosis,
        actions_performed=intervention.actions_performed or "",
        equipment_involved=intervention.equipment_involved,
        materials_used=intervention.materials_used,
        tests_performed=intervention.tests_performed,
        result=intervention.result,
        follow_up=intervention.follow_up,
        resolution_notes=intervention.resolution_notes,
        technician_notes=intervention.technician_notes,
        agency_comments=intervention.agency_comments,
        technician_user_id=intervention.technician_user_id,
        technician_name=intervention.technician.full_name if intervention.technician else None,
        created_at=intervention.created_at,
        updated_at=intervention.updated_at,
        review_status=intervention.review_status,
        review_feedback=intervention.review_feedback,
        reviewed_by_user_id=intervention.reviewed_by_user_id,
        reviewed_by_name=intervention.reviewed_by.full_name if intervention.reviewed_by else None,
        reviewed_at=intervention.reviewed_at,
        user_validated_at=intervention.user_validated_at,
    )


def team_schema(team: Team) -> TeamSchema:
    return TeamSchema(id=team.id, name=team.name, slug=team.slug, description=team.description, default_queue=team.default_queue)


def agent_schema(agent: Agent) -> AgentSchema:
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
