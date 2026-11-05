"""Exercise one end-user to support-agent workflow in each tenant."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from backend.ai.model import TicketRoutingModel
from backend.auth.service import AuthService
from backend.db.session import SessionLocal
from backend.models import Role, User, UserAgency
from backend.seed.demo import reference_training_rows
from backend.services.tickets import TicketService


def main() -> None:
    with SessionLocal() as db:
        model = TicketRoutingModel()
        model.train(reference_training_rows())
        service = TicketService(db, model)
        auth = AuthService(db)
        support = db.execute(select(User).join(Role).where(Role.name == "Support_IT")).scalars().first()
        if not support:
            raise RuntimeError("Support account is missing.")

        for agency in ("Global Voyages", "Trésor Voyages"):
            assignment, user = db.execute(
                select(UserAgency, User)
                .join(User, User.id == UserAgency.user_id)
                .where(UserAgency.agency == agency, UserAgency.station.is_not(None))
                .order_by(UserAgency.station, UserAgency.post)
            ).first()

            ticket = service.create_ticket(
                requester_user_id=user.id,
                created_by_user_id=user.id,
                subject="ID Colis très lent sur ancien ordinateur HP",
                description="Je travaille sur un ancien ordinateur HP. L'application ID Colis est très lente et ralentit l'enregistrement des colis.",
                metadata={
                    "agency": agency,
                    "site": assignment.station,
                    "city": "Douala" if assignment.station.startswith("DLA-") else assignment.station.split(" ", 1)[0],
                    "operational_impact": "Individuel",
                    "field_intervention_required": False,
                },
            )

            support_session = auth.sign_in(None, "Support123!", agency, None, support.full_name)
            support_user = auth.current_user(support_session.access_token)
            visible = service.list_tickets(support_user)
            if not any(item.id == ticket.id for item in visible):
                raise AssertionError(f"Support account cannot see its {agency} ticket.")

            service.add_comment(
                ticket.id,
                support.id,
                "Support_IT",
                "Nous avons bien reçu votre signalement. Le support va intervenir pour analyser les performances de cet ancien ordinateur HP et vous permettre de reprendre votre travail.",
            )
            updated = service.change_status(ticket.id, "En cours", support.id)
            print(f"{agency}: user={user.full_name} station={assignment.station} ticket={updated.id} category={updated.category} priority={updated.priority} status={updated.status} support_visible=yes")


if __name__ == "__main__":
    main()
