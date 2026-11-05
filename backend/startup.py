from __future__ import annotations

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from .ai.model import TicketRoutingModel
from .db.session import engine
from .models import AgencyStation, Role, Ticket, User, UserAgency
from .seed.demo import ensure_demo_data
from .services.tickets import TicketService


def _ensure_columns(table: str, additions: dict[str, str]) -> None:
    """Add missing columns to an existing development database.

    A lightweight stand-in for a real migration tool: safe to call on every
    startup, and new columns for any table can be added here without a
    bespoke function per change. Deliberate, intentional schema changes
    should still go through an Alembic revision (see docs/OPERATIONS.md).
    """
    columns = {column["name"] for column in inspect(engine).get_columns(table)}
    missing = {name: definition for name, definition in additions.items() if name not in columns}
    if not missing:
        return
    with engine.begin() as connection:
        for name, definition in missing.items():
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))


def run_schema_migrations() -> None:
    """Table/column additions applied on every startup, in order."""
    _ensure_columns(
        "interventions",
        {
            "review_status": "VARCHAR(30) NOT NULL DEFAULT 'En attente de validation'",
            "review_feedback": "TEXT",
            "reviewed_by_user_id": "VARCHAR(36)",
            "reviewed_at": "DATETIME",
            "user_validated_at": "DATETIME",
        },
    )


def seed_directory(db: Session) -> None:
    """Seed the initial agency/station directory without mixing tenants."""
    rows = [
        ("Global Voyages", "Bafoussam Centre", "Bafoussam", "Quartier Ndiengso", "690694318"),
        ("Global Voyages", "Yaoundé Centre", "Yaoundé", "Centre-ville", "690694318"),
        ("Global Voyages", "Biyem-Assi", "Yaoundé", "Carrefour Biyem-Assi", "656674860"),
        ("Global Voyages", "DLA-Bépanda", "Douala", "Quartier Bépanda", "658595989"),
        ("Global Voyages", "DLA-Brazzaville", "Douala", "Quartier Brazzaville", "690643275"),
        ("Global Voyages", "DLA-Mboppi", "Douala", "Quartier Mboppi", "690674364"),
        ("Global Voyages", "DLA-Village", "Douala", "Entrée-billes", "690029529"),
        ("Global Voyages", "Douala Akwa", "Douala", "Akwa", "692339031"),
        ("Trésor Voyages", "Bafoussam Centre", "Bafoussam", "Quartier Ndiengso", "691832408"),
        ("Trésor Voyages", "Baneghang", "Baneghang", "Baneghang", "692105461"),
        ("Trésor Voyages", "DLA-Bépanda", "Douala", "Quartier Bépanda", "691832671"),
        ("Trésor Voyages", "DLA-Bonabéri", "Douala", "Quartier Bonabéri", "691832670"),
        ("Trésor Voyages", "DLA-Brazzaville", "Douala", "Quartier Brazzaville", "691832672"),
        ("Trésor Voyages", "DLA-Village", "Douala", "Quartier Village", "695612260"),
        ("Trésor Voyages", "Dschang", "Dschang", "Entrée de la ville", "691832148"),
        ("Trésor Voyages", "Mvan 2", "Yaoundé", "Yaoundé", "690529802"),
    ]
    desired = {(agency, name) for agency, name, *_ in rows}
    for station in db.execute(select(AgencyStation)).scalars().all():
        if (station.agency, station.name) not in desired:
            db.delete(station)
    existing = {(s.agency, s.name) for s in db.execute(select(AgencyStation)).scalars().all()}
    for agency, name, city, address, phone in rows:
        if (agency, name) not in existing:
            db.add(AgencyStation(agency=agency, name=name, city=city, address=address, phone=phone, posts_json=[{"name": "Vente / dépôt", "assigned_user": None}, {"name": "Expédition / retrait", "assigned_user": None}]))
    db.commit()


def backfill_demo_ticket_tenants(db: Session) -> None:
    """Keep legacy demo tickets visible in exactly one tenant queue.

    Must run after seed_user_agencies, so each requester's real UserAgency
    assignment is available: a ticket backfilled to the wrong tenant would
    leak into (or vanish from) a support queue its requester doesn't belong to.
    """
    unassigned = db.execute(select(Ticket).where(Ticket.agency.is_(None)).order_by(Ticket.created_at.asc())).scalars().all()
    if not unassigned:
        return
    assignments = {a.user_id: a.agency for a in db.execute(select(UserAgency)).scalars().all()}
    fallback_index = 0
    for ticket in unassigned:
        agency = assignments.get(ticket.requester_user_id)
        if not agency:
            agency = "Global Voyages" if fallback_index % 2 == 0 else "Trésor Voyages"
            fallback_index += 1
        ticket.agency = agency
    db.commit()


def seed_user_agencies(db: Session) -> None:
    """Ensure every station has two exclusive demo workstation users."""
    from .auth.service import hash_password

    stations = {agency: db.execute(select(AgencyStation).where(AgencyStation.agency == agency).order_by(AgencyStation.name)).scalars().all() for agency in ("Global Voyages", "Trésor Voyages")}
    users = db.execute(select(User).join(Role).where(Role.name == "Utilisateur").order_by(User.email)).scalars().all()
    role = db.execute(select(Role).where(Role.name == "Utilisateur")).scalar_one()
    required = sum(len(items) * 2 for items in stations.values())
    demo_names = ["Aline Kamga", "Boris Tchana", "Clarisse Ndomo", "Didier Foka", "Estelle Mvondo", "Franck Tamba", "Grace Ngu", "Hervé Mballa", "Irene Njoya", "Junior Ebong", "Kevin Meka", "Laure Mbianda", "Mireille Nono", "Nadia Fotso", "Olivier Toko", "Prisca Muna", "Rosine Abena", "Serge Biloa", "Thérèse Etoa", "Ulrich Nsame", "Valérie Kenne", "Wilfried Momo"]
    for index in range(len(users), required):
        user = User(email=f"station.user{index + 1}@idcolis.cm", full_name=demo_names[index - 10] if index - 10 < len(demo_names) else f"Agent agence {index + 1}", password_hash=hash_password("IDColis2024!"), role_id=role.id, is_active=True, region="Littoral", department="Opérations")
        db.add(user)
        db.flush()
        users.append(user)
    for index, user in enumerate(users):
        if user.full_name.startswith("Utilisateur station") and index - 10 < len(demo_names):
            user.full_name = demo_names[index - 10]
    for assignment in db.execute(select(UserAgency)).scalars().all():
        db.delete(assignment)
    db.flush()
    index = 0
    for agency, agency_stations in stations.items():
        for station in agency_stations:
            for post in ("Vente / dépôt", "Expédition / retrait"):
                db.add(UserAgency(user_id=users[index].id, agency=agency, station=station.name, post=post))
                index += 1
    db.commit()


def seed_regulators(db: Session) -> None:
    """Ensure one agency-scoped regulator account exists per tenant."""
    from .auth.service import hash_password

    role = db.execute(select(Role).where(Role.name == "Régulateur_Agence")).scalar_one_or_none()
    if not role:
        role = Role(name="Régulateur_Agence", description="Validateur opérationnel limité à son agence")
        db.add(role)
        db.commit()
        db.refresh(role)
    for email, name, agency in [
        ("regulateur.tresor@idcolis.cm", "Régulateur Trésor Voyages", "Trésor Voyages"),
        ("regulateur.global@idcolis.cm", "Régulateur Global Voyages", "Global Voyages"),
    ]:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not user:
            user = User(email=email, full_name=name, password_hash=hash_password("Regulator123!"), role_id=role.id, is_active=True)
            db.add(user)
            db.flush()
        assignment = db.execute(select(UserAgency).where(UserAgency.user_id == user.id)).scalar_one_or_none()
        if not assignment:
            db.add(UserAgency(user_id=user.id, agency=agency))
    db.commit()


def run_startup_tasks(db: Session, classifier: TicketRoutingModel) -> None:
    """Everything the API needs to do once, in order, before serving traffic."""
    run_schema_migrations()
    # Roles, teams, and the base demo users must exist before the agency,
    # directory, and regulator seeding below, which assume them.
    ensure_demo_data(db)
    seed_directory(db)
    seed_user_agencies(db)
    seed_regulators(db)
    backfill_demo_ticket_tenants(db)

    ticket_service = TicketService(db, classifier)
    training_rows = ticket_service.get_training_data()
    if training_rows:
        classifier.train(training_rows)
    else:
        classifier.load()
