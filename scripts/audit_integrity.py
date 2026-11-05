"""Read-only integrity audit for the linked ID Colis workflow data."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from backend.db.session import SessionLocal  # noqa: E402
from backend.models import (  # noqa: E402
    AgencyStation,
    Agent,
    Intervention,
    InterventionAttachment,
    Role,
    Team,
    Ticket,
    TicketComment,
    User,
    UserAgency,
)

ALLOWED_STATUSES = {"Créé", "Assigné", "En attente", "En cours", "En attente de validation", "À corriger", "Résolu", "Clôturé"}
AGENCIES = {"Trésor Voyages", "Global Voyages"}


def main() -> int:
    issues: list[str] = []
    with SessionLocal() as db:
        users = db.execute(select(User)).scalars().all()
        roles = {role.id: role.name for role in db.execute(select(Role)).scalars().all()}
        assignments = {item.user_id: item for item in db.execute(select(UserAgency)).scalars().all()}
        tickets = db.execute(select(Ticket)).scalars().all()
        interventions = db.execute(select(Intervention)).scalars().all()
        comments = db.execute(select(TicketComment)).scalars().all()
        attachments = db.execute(select(InterventionAttachment)).scalars().all()
        stations = db.execute(select(AgencyStation)).scalars().all()
        agents = db.execute(select(Agent)).scalars().all()
        teams = db.execute(select(Team)).scalars().all()

        for user in users:
            role = roles.get(user.role_id)
            if role != "Support_IT" and user.id not in assignments:
                issues.append(f"user without agency assignment: {user.email}")
            if role == "Régulateur_Agence" and (user.id not in assignments or assignments[user.id].station is not None):
                issues.append(f"regulator is not agency-wide: {user.email}")
        for station in stations:
            if station.agency not in AGENCIES:
                issues.append(f"unknown station agency: {station.agency}/{station.name}")
            if station.city not in station.name and station.name.startswith("Douala ") and station.name == "Douala Bafoussam":
                issues.append(f"mixed city/station name: {station.name}")
        user_ids = {user.id for user in users}
        team_ids = {team.id for team in teams}
        agent_ids = {agent.id for agent in agents}
        ticket_ids = {ticket.id for ticket in tickets}
        intervention_ids = {item.id for item in interventions}
        for ticket in tickets:
            if ticket.requester_user_id not in user_ids or ticket.created_by_user_id not in user_ids:
                issues.append(f"ticket has missing user link: {ticket.id}")
            if ticket.team_id not in team_ids:
                issues.append(f"ticket has missing team link: {ticket.id}")
            if ticket.assigned_agent_id and ticket.assigned_agent_id not in agent_ids:
                issues.append(f"ticket has missing agent link: {ticket.id}")
            if ticket.status not in ALLOWED_STATUSES:
                issues.append(f"ticket has invalid status: {ticket.id}/{ticket.status}")
            requester_assignment = assignments.get(ticket.requester_user_id)
            if requester_assignment and ticket.agency != requester_assignment.agency:
                issues.append(f"ticket agency differs from requester: {ticket.id}")
        for item in interventions:
            if item.ticket_id not in ticket_ids:
                issues.append(f"intervention has missing ticket link: {item.id}")
            if item.technician_user_id and item.technician_user_id not in user_ids:
                issues.append(f"intervention has missing technician link: {item.id}")
            ticket = next((candidate for candidate in tickets if candidate.id == item.ticket_id), None)
            if ticket and item.agency and item.agency != ticket.agency:
                issues.append(f"intervention agency differs from ticket: {item.intervention_number}")
        for comment in comments:
            if comment.ticket_id not in ticket_ids or comment.author_user_id not in user_ids:
                issues.append(f"comment has broken link: {comment.id}")
        for attachment in attachments:
            if attachment.intervention_id not in intervention_ids or attachment.uploaded_by_user_id not in user_ids:
                issues.append(f"attachment has broken link: {attachment.id}")

        print(f"users={len(users)} tickets={len(tickets)} interventions={len(interventions)} comments={len(comments)} attachments={len(attachments)}")
        print("ticket_statuses=" + repr(dict(Counter(ticket.status for ticket in tickets))))
        print("agency_ticket_counts=" + repr(dict(Counter(ticket.agency for ticket in tickets))))
        print("stations=" + repr(sorted((station.agency, station.name, station.city) for station in stations)))
        if issues:
            print("FAIL")
            for issue in issues:
                print("- " + issue)
            return 1
        print("PASS: all checked user, agency, station, ticket, intervention, comment, and attachment links are valid")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
