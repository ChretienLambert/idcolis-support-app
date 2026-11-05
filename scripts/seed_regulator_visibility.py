from sqlalchemy import select

from backend.ai.model import TicketRoutingModel
from backend.db.session import SessionLocal
from backend.models import User, UserAgency
from backend.services.tickets import TicketService


def main() -> None:
    with SessionLocal() as db:
        model = TicketRoutingModel()
        model.load()
        service = TicketService(db, model)
        for agency in ("Trésor Voyages", "Global Voyages"):
            assignment, user = db.execute(
                select(UserAgency, User)
                .join(User, User.id == UserAgency.user_id)
                .where(UserAgency.agency == agency, UserAgency.station.is_not(None))
                .order_by(UserAgency.station, UserAgency.post)
            ).first()
            untouched = service.create_ticket(
                requester_user_id=user.id,
                created_by_user_id=user.id,
                subject=f"Test visibilité régulateur - {agency}",
                description="Ticket de test pour vérifier la visibilité complète de l’agence.",
                metadata={"agency": agency, "site": assignment.station, "city": assignment.station.split(" ", 1)[0], "operational_impact": "Individuel"},
            )
            handled = service.create_ticket(
                requester_user_id=user.id,
                created_by_user_id=user.id,
                subject=f"Test ticket déjà traité - {agency}",
                description="Ticket de test déjà pris en charge par le support IT.",
                metadata={"agency": agency, "site": assignment.station, "city": assignment.station.split(" ", 1)[0], "operational_impact": "Individuel"},
            )
            handled.status = "En cours"
            db.commit()
            print(agency, untouched.id, untouched.status, handled.id, handled.status)


if __name__ == "__main__":
    main()
