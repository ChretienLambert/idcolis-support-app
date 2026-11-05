from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select

from backend.db.base import Base
from backend.db.session import SessionLocal, engine
from backend.models import (
    AIPrediction,
    Agent,
    AuditLog,
    Intervention,
    InterventionAttachment,
    RefreshSession,
    Ticket,
    TicketComment,
    User,
    UserAgency,
)
from backend.seed.demo import ensure_demo_data
from backend.startup import seed_directory, seed_regulators, seed_user_agencies

Base.metadata.create_all(bind=engine)


def main() -> None:
    db = SessionLocal()
    try:
        # User-linked records must be removed before users because the schema
        # uses foreign keys without database-level cascade deletes.
        for model in (
            InterventionAttachment,
            Intervention,
            TicketComment,
            AIPrediction,
            Ticket,
            AuditLog,
            RefreshSession,
            UserAgency,
            Agent,
            User,
        ):
            db.execute(delete(model))
        db.commit()

        ensure_demo_data(db)
        seed_directory(db)
        seed_user_agencies(db)
        # seed_user_agencies rebuilds all assignments, so regulators must be
        # attached after the station-user assignments are recreated.
        seed_regulators(db)
        db.commit()

        users = db.execute(select(User).order_by(User.email)).scalars().all()
        print(f"Recreated {len(users)} users")
        for user in users:
            assignment = db.query(UserAgency).filter(UserAgency.user_id == user.id).first()
            print(f"{user.email} | {user.role.name} | {assignment.agency if assignment else '-'} | {assignment.station if assignment else '-'}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
