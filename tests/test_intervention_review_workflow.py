from __future__ import annotations

from sqlalchemy import select

from backend.db.session import SessionLocal
from backend.models import User, UserAgency

from conftest import auth_headers, login

SUPPORT_EMAIL = "support@idcolis.cm"
SUPPORT_PASSWORD = "Support123!"
STATION_PASSWORD = "IDColis2024!"
REGULATOR_PASSWORD = "Regulator123!"


def _station_user(agency: str) -> dict:
    with SessionLocal() as db:
        assignment, user = db.execute(
            select(UserAgency, User)
            .join(User, User.id == UserAgency.user_id)
            .where(UserAgency.agency == agency, UserAgency.station.is_not(None))
            .order_by(UserAgency.station, UserAgency.post)
        ).first()
        return {"full_name": user.full_name, "agency": assignment.agency, "station": assignment.station}


def _create_ticket(client, agency: str) -> dict:
    requester = _station_user(agency)
    session = login(client, name=requester["full_name"], password=STATION_PASSWORD, agency=requester["agency"], station=requester["station"])
    response = client.post(
        "/tickets",
        headers=auth_headers(session),
        json={
            "subject": "Scanner hors service au dépôt",
            "description": "Le scanner de colis ne répond plus depuis ce matin.",
            "site": requester["station"],
        },
    )
    assert response.status_code == 200, response.text
    ticket = response.json()
    assert ticket["agency"] == agency
    return {"ticket": ticket, "requester_session": session, "requester": requester}


def test_full_regulator_review_and_correction_loop(client):
    created = _create_ticket(client, "Global Voyages")
    ticket_id = created["ticket"]["id"]

    support_session = login(client, email=SUPPORT_EMAIL, password=SUPPORT_PASSWORD, agency="Global Voyages")
    support_headers = auth_headers(support_session)

    intervention_response = client.post(
        f"/tickets/{ticket_id}/interventions",
        headers=support_headers,
        json={"diagnosis": "Capteur du scanner encrassé.", "actions_performed": "Nettoyage du capteur.", "result": "En cours"},
    )
    assert intervention_response.status_code == 200, intervention_response.text
    intervention = intervention_response.json()
    intervention_id = intervention["id"]

    ticket_after_create = client.get(f"/tickets/{ticket_id}", headers=support_headers).json()
    assert ticket_after_create["status"] == "En cours"

    resolve_response = client.patch(
        f"/interventions/{intervention_id}",
        headers=support_headers,
        json={"result": "Résolu", "resolution_notes": "Scanner opérationnel après nettoyage."},
    )
    assert resolve_response.status_code == 200, resolve_response.text
    assert resolve_response.json()["review_status"] == "En attente de validation"

    ticket_awaiting_review = client.get(f"/tickets/{ticket_id}", headers=support_headers).json()
    assert ticket_awaiting_review["status"] == "En attente de validation"

    regulator_session = login(client, email="regulateur.global@idcolis.cm", password=REGULATOR_PASSWORD, agency="Global Voyages")
    regulator_headers = auth_headers(regulator_session)

    correction_response = client.post(
        f"/interventions/{intervention_id}/review",
        headers=regulator_headers,
        json={"decision": "correction_required", "feedback": "Préciser le numéro de série du scanner remplacé."},
    )
    assert correction_response.status_code == 200, correction_response.text
    assert correction_response.json()["review_status"] == "À corriger"

    ticket_needs_correction = client.get(f"/tickets/{ticket_id}", headers=support_headers).json()
    assert ticket_needs_correction["status"] == "À corriger"

    # A missing correction feedback must be rejected.
    missing_feedback = client.post(
        f"/interventions/{intervention_id}/review",
        headers=regulator_headers,
        json={"decision": "correction_required", "feedback": "   "},
    )
    assert missing_feedback.status_code == 400

    corrected_response = client.patch(
        f"/interventions/{intervention_id}",
        headers=support_headers,
        json={"resolution_notes": "Scanner SN-4821 remplacé et testé."},
    )
    assert corrected_response.status_code == 200, corrected_response.text
    assert corrected_response.json()["review_status"] == "En attente de validation"

    approve_response = client.post(
        f"/interventions/{intervention_id}/review",
        headers=regulator_headers,
        json={"decision": "approved"},
    )
    assert approve_response.status_code == 200, approve_response.text
    assert approve_response.json()["review_status"] == "Approuvée"

    ticket_approved = client.get(f"/tickets/{ticket_id}", headers=support_headers).json()
    assert ticket_approved["status"] == "En attente de validation"

    validate_response = client.post(f"/tickets/{ticket_id}/validate", headers=auth_headers(created["requester_session"]))
    assert validate_response.status_code == 200, validate_response.text
    assert validate_response.json()["status"] == "Résolu"

    # Once approved and validated, the intervention is closed for further edits.
    locked_response = client.patch(
        f"/interventions/{intervention_id}",
        headers=support_headers,
        json={"resolution_notes": "Tentative de modification après clôture."},
    )
    assert locked_response.status_code == 409


def test_validate_rejects_ticket_not_yet_approved(client):
    created = _create_ticket(client, "Global Voyages")
    ticket_id = created["ticket"]["id"]

    response = client.post(f"/tickets/{ticket_id}/validate", headers=auth_headers(created["requester_session"]))
    assert response.status_code == 400


def test_support_cannot_create_intervention_on_another_agency_ticket(client):
    created = _create_ticket(client, "Trésor Voyages")
    ticket_id = created["ticket"]["id"]

    support_session = login(client, email=SUPPORT_EMAIL, password=SUPPORT_PASSWORD, agency="Global Voyages")
    response = client.post(
        f"/tickets/{ticket_id}/interventions",
        headers=auth_headers(support_session),
        json={"diagnosis": "Tentative inter-agence."},
    )
    assert response.status_code == 403


def test_regulator_cannot_review_another_agency_intervention(client):
    created = _create_ticket(client, "Trésor Voyages")
    ticket_id = created["ticket"]["id"]

    tresor_support = login(client, email=SUPPORT_EMAIL, password=SUPPORT_PASSWORD, agency="Trésor Voyages")
    intervention = client.post(
        f"/tickets/{ticket_id}/interventions",
        headers=auth_headers(tresor_support),
        json={"diagnosis": "Panne réseau locale."},
    ).json()

    global_regulator = login(client, email="regulateur.global@idcolis.cm", password=REGULATOR_PASSWORD, agency="Global Voyages")
    response = client.post(
        f"/interventions/{intervention['id']}/review",
        headers=auth_headers(global_regulator),
        json={"decision": "approved"},
    )
    assert response.status_code == 403
