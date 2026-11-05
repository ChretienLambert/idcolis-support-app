from sqlalchemy import select

from backend.ai.model import TicketRoutingModel
from backend.auth.service import AuthService
from backend.db.session import SessionLocal
from backend.models import Intervention, Role, User, UserAgency, utcnow
from backend.services.tickets import TicketService


def main() -> None:
    with SessionLocal() as db:
        model = TicketRoutingModel()
        model.load()
        service = TicketService(db, model)
        requester = db.execute(select(User).join(UserAgency).where(UserAgency.agency == "Trésor Voyages")).scalars().first()
        support = db.execute(select(User).join(Role).where(Role.name == "Support_IT")).scalars().first()
        regulator = db.execute(select(User).join(Role).where(Role.name == "Régulateur_Agence", User.full_name.like("%Trésor%"))).scalars().first()
        assignment = db.execute(select(UserAgency).where(UserAgency.user_id == requester.id)).scalar_one()
        ticket = service.create_ticket(
            requester_user_id=requester.id,
            created_by_user_id=requester.id,
            subject="Scanner de retrait en panne - workflow validation",
            description="Le scanner du poste de retrait ne lit plus les codes-barres.",
            metadata={"agency": assignment.agency, "site": assignment.station, "city": "Bafoussam", "operational_impact": "Poste"},
        )
        ticket.status = "Assigné"
        db.commit()
        for number, feedback in [(1, "Le diagnostic est incomplet : vérifier le câble et refaire le test."), (2, "Le test matériel manque encore : joindre le résultat du test avec un autre scanner.")]:
            intervention = Intervention(
                ticket_id=ticket.id,
                intervention_number=f"INT-{ticket.id}-{number}",
                agency=ticket.agency,
                site=ticket.site,
                city=ticket.city,
                technician_user_id=support.id,
                diagnosis="Scanner non reconnu",
                actions_performed=f"Intervention {number}: vérification et correction du poste.",
                tests_performed="Test de lecture effectué.",
                result="Résolu",
                review_status="En attente de validation",
            )
            db.add(intervention)
            ticket.status = "En attente de validation"
            db.commit()
            intervention.review_status = "À corriger"
            intervention.review_feedback = feedback
            intervention.reviewed_by_user_id = regulator.id
            intervention.reviewed_at = utcnow()
            ticket.status = "À corriger"
            db.commit()
            service.add_comment(ticket.id, regulator.id, regulator.role.name, feedback, is_internal=True)

        final = Intervention(
            ticket_id=ticket.id,
            intervention_number=f"INT-{ticket.id}-3",
            agency=ticket.agency,
            site=ticket.site,
            city=ticket.city,
            technician_user_id=support.id,
            diagnosis="Scanner non reconnu",
            actions_performed="Câble remplacé et scanner réinstallé.",
            tests_performed="Test avec trois colis réussi.",
            result="Résolu",
            review_status="Approuvée",
            reviewed_by_user_id=regulator.id,
            reviewed_at=utcnow(),
        )
        db.add(final)
        db.flush()
        ticket.status = "Résolu"
        ticket.resolved_at = utcnow()
        final.user_validated_at = utcnow()
        db.commit()
        print(f"ticket={ticket.id} status={ticket.status} interventions=3 corrections=2 user_validated=yes")


if __name__ == "__main__":
    main()
