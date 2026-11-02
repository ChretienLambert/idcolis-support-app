"""Replace stale demo tickets with current ID Colis agency-user tickets."""

from sqlalchemy import delete, select

from backend.app import _seed_directory, _seed_user_agencies, ensure_demo_data, classifier
from backend.db.session import SessionLocal
from backend.models import AIPrediction, AuditLog, Ticket, TicketComment, User, UserAgency
from backend.services.tickets import TicketService
from backend.seed.demo import reference_training_rows


TICKETS = [
    ("Scanner de vente non reconnu", "Le scanner du poste de vente ne lit plus les codes-barres des colis.", "scanning-hardware"),
    ("Manifestes non synchronisés", "Le manifeste du départ reste en attente et les colis ne remontent pas dans ID Colis.", "waybill-sync"),
    ("Compte agent bloqué", "Le compte de l'agent est bloqué après plusieurs tentatives de connexion.", "identity-access"),
    ("Connexion internet instable", "La connexion réseau se coupe régulièrement pendant l'enregistrement des colis.", "network-connectivity"),
    ("Application chauffeur inaccessible", "L'application chauffeur affiche une erreur au démarrage.", "fleet-driver"),
    ("Imprimante de retrait hors service", "Les reçus de retrait ne peuvent plus être imprimés au poste expédition.", "scanning-hardware"),
    ("Waybill introuvable", "Un bordereau créé ce matin n'est pas visible dans la recherche.", "waybill-sync"),
    ("Mot de passe oublié", "L'agent demande la réinitialisation de son mot de passe ID Colis.", "identity-access"),
    ("Wi-Fi indisponible au comptoir", "Le Wi-Fi de l'agence est indisponible pour les deux postes.", "network-connectivity"),
    ("Synchronisation urgente des départs", "Les manifestes de plusieurs départs sont bloqués et l'activité de l'agence est interrompue.", "waybill-sync"),
    ("Terminal de scan endommagé", "Le terminal ne s'allume plus après une chute au poste de vente.", "scanning-hardware"),
    ("Compte nouvel agent à créer", "Un nouvel agent doit être ajouté au poste expédition.", "identity-access"),
    ("Erreur application chauffeur", "Le trajet du chauffeur ne se met pas à jour dans l'application.", "fleet-driver"),
    ("Réseau lent à l'agence", "Les pages ID Colis chargent très lentement depuis ce matin.", "network-connectivity"),
    ("Doublon de colis dans le manifeste", "Le même colis apparaît deux fois dans le manifeste du départ.", "waybill-sync"),
    ("Lecteur code-barres intermittent", "Le lecteur fonctionne une fois sur deux au poste de retrait.", "scanning-hardware"),
]


def main() -> None:
    with SessionLocal() as db:
        ensure_demo_data(db)
        _seed_directory(db)
        _seed_user_agencies(db)
        for model in (TicketComment, AIPrediction, Ticket, AuditLog):
            db.execute(delete(model))
        db.commit()

        classifier.train(reference_training_rows())
        service = TicketService(db, classifier)
        assignments = db.execute(select(UserAgency, User).join(User, User.id == UserAgency.user_id).order_by(UserAgency.agency, UserAgency.station, UserAgency.post)).all()
        if not assignments:
            raise RuntimeError("No agency users were found after seeding the directory.")
        assignments_by_agency = {}
        for assignment, user in assignments:
            assignments_by_agency.setdefault(assignment.agency, []).append((assignment, user))
        agency_names = sorted(assignments_by_agency)

        for index, (subject, description, _team) in enumerate(TICKETS):
            agency_assignments = assignments_by_agency[agency_names[index % len(agency_names)]]
            assignment, user = agency_assignments[(index // len(agency_names)) % len(agency_assignments)]
            service.create_ticket(
                requester_user_id=user.id,
                subject=subject,
                description=description,
                created_by_user_id=user.id,
                metadata={
                    "agency": assignment.agency,
                    "site": assignment.station,
                    "city": assignment.station.split("-")[0] if "-" in assignment.station else assignment.station,
                    "operational_impact": "Agence" if index % 3 == 0 else "Individuel",
                    "field_intervention_required": index % 4 == 0,
                },
            )
        print(f"Seeded {len(TICKETS)} current tickets for {len(assignments)} agency posts.")


if __name__ == "__main__":
    main()
