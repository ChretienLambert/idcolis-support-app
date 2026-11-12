from __future__ import annotations

from conftest import auth_headers, login


def test_classify_low_confidence_fallback_returns_a_real_team(client):
    session = login(client, email="support@idcolis.cm", password="Support123!", agency="Global Voyages")

    response = client.post(
        "/ai/classify",
        headers=auth_headers(session),
        json={"subject": "Chaise cassée", "description": "La chaise du bureau est cassée.", "agency": "Global Voyages"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["category"] == "Autres"
    assert body["team_slug"] == "identity-access"
    assert body["team_name"] == "ID Colis accès et support"
