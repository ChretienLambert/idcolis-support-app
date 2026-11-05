from __future__ import annotations

import logging
import sys
from pathlib import Path
from dataclasses import asdict
from typing import Any

import httpx

# Add parent directory to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from constants import BACKEND_URL
from services.logging import build_logger


class APIError(RuntimeError):
    pass


class BackendAPI:
    def __init__(self, base_url: str = BACKEND_URL) -> None:
        self.client = httpx.Client(base_url=base_url, timeout=20.0)
        self.logger = build_logger("ID Colis.frontend.api", "frontend.log")

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self.client.request(method, path, **kwargs)
            self.logger.info("%s %s status=%s", method.upper(), path, response.status_code)
            return response
        except httpx.ConnectError as exc:
            self.logger.warning("%s %s connect_error=%s", method.upper(), path, exc)
            raise APIError("Backend is unavailable right now. Start the FastAPI server on http://localhost:8000 and try again.") from exc
        except httpx.TimeoutException as exc:
            self.logger.warning("%s %s timeout=%s", method.upper(), path, exc)
            raise APIError("Backend request timed out. Please try again in a moment.") from exc

    def _json(self, response: httpx.Response) -> dict[str, Any] | list[dict[str, Any]]:
        if response.status_code >= 400:
            try:
                payload = response.json()
                detail = payload.get("detail", response.text) if isinstance(payload, dict) else response.text
            except ValueError:
                detail = response.text or f"Backend returned HTTP {response.status_code}."
            raise APIError(str(detail))
        try:
            return response.json()
        except ValueError as exc:
            self.logger.error("invalid_json_response status=%s body=%s", response.status_code, response.text[:500])
            raise APIError("Le serveur a renvoyé une réponse invalide. Consultez les journaux du backend.") from exc

    def login(self, name: str, password: str, agency: str | None = None, station: str | None = None) -> dict[str, Any]:
        self.logger.info("login_attempt name=%s", name)
        response = self._request("POST", "/auth/login", json={"name": name, "password": password, "agency": agency, "station": station})
        if response.status_code >= 400:
            self.logger.info("login_failed name=%s status=%s", name, response.status_code)
        else:
            self.logger.info("login_success name=%s status=%s", name, response.status_code)
        return self._json(response)  # type: ignore

    def restore(self, session_id: str, session_key: str, agency: str | None = None) -> dict[str, Any]:
        return self._json(self._request("POST", "/auth/restore", json={"session_id": session_id, "session_key": session_key, "agency": agency}))  # type: ignore

    def logout(self, session_id: str | None = None, session_key: str | None = None) -> dict[str, Any]:
        return self._json(self._request("POST", "/auth/logout", json={"session_id": session_id, "session_key": session_key}))  # type: ignore

    def me(self, access_token: str) -> dict[str, Any]:
        return self._json(self._request("GET", "/auth/me", headers={"Authorization": f"Bearer {access_token}"}))  # type: ignore

    def list_tickets(self, access_token: str, agency: str | None = None) -> list[dict[str, Any]]:
        params = {"agency": agency} if agency else None
        response = self._request("GET", "/tickets", params=params, headers={"Authorization": f"Bearer {access_token}"})
        payload = self._json(response)
        self.logger.info("tickets_loaded agency=%s count=%s", agency, len(payload) if isinstance(payload, list) else "invalid")
        return payload  # type: ignore

    def directory(self, access_token: str) -> list[dict[str, Any]]:
        return self._json(self._request("GET", "/directory", headers={"Authorization": f"Bearer {access_token}"}))  # type: ignore

    def public_agents(self, agency: str, station: str) -> list[dict[str, Any]]:
        return self._json(self._request("GET", "/public/agents", params={"agency": agency, "station": station}))  # type: ignore

    def list_teams(self, access_token: str) -> list[dict[str, Any]]:
        return self._json(self._request("GET", "/teams", headers={"Authorization": f"Bearer {access_token}"}))  # type: ignore

    def list_agents(self, access_token: str, team_id: str | None = None) -> list[dict[str, Any]]:
        params = {"team_id": team_id} if team_id else None
        return self._json(self._request("GET", "/agents", headers={"Authorization": f"Bearer {access_token}"}, params=params))  # type: ignore

    def get_ticket(self, access_token: str, ticket_id: str) -> dict[str, Any]:
        return self._json(self._request("GET", f"/tickets/{ticket_id}", headers={"Authorization": f"Bearer {access_token}"}))  # type: ignore

    def create_ticket(self, access_token: str, subject: str, description: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"subject": subject, "description": description}
        if metadata:
            payload.update(metadata)
        return self._json(
            self._request(
                "POST",
                "/tickets",
                headers={"Authorization": f"Bearer {access_token}"},
                json=payload,
            )
        )  # type: ignore

    def update_ticket(self, access_token: str, ticket_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json(self._request("PATCH", f"/tickets/{ticket_id}", headers={"Authorization": f"Bearer {access_token}"}, json=payload))  # type: ignore

    def assign_ticket(self, access_token: str, ticket_id: str, to_team_id: str | None = None, to_agent_id: str | None = None, reason: str = "") -> dict[str, Any]:
        return self._json(
            self._request(
                "POST",
                f"/tickets/{ticket_id}/assign",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"to_team_id": to_team_id, "to_agent_id": to_agent_id, "reason": reason},
            )
        )  # type: ignore

    def add_comment(self, access_token: str, ticket_id: str, body: str, is_internal: bool = False) -> dict[str, Any]:
        return self._json(
            self._request(
                "POST",
                f"/tickets/{ticket_id}/comments",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"body": body, "is_internal": is_internal},
            )
        )  # type: ignore

    def change_status(self, access_token: str, ticket_id: str, status_value: str) -> dict[str, Any]:
        return self._json(
            self._request(
                "POST",
                f"/tickets/{ticket_id}/status",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"status": status_value},
            )
        )  # type: ignore

    def approve_ai_suggestions(self, access_token: str, ticket_id: str, category: str, priority: str, team_slug: str, corrected: bool = False, service_concerne: str | None = None) -> dict[str, Any]:
        params = {"category": category, "priority": priority, "team_slug": team_slug, "corrected": corrected}
        if service_concerne:
            params["service_concerne"] = service_concerne
        return self._json(
            self._request(
                "POST",
                f"/tickets/{ticket_id}/approve",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
        )  # type: ignore

    def classify(self, access_token: str, subject: str, description: str, agency: str | None = None) -> dict[str, Any]:
        return self._json(
            self._request(
                "POST",
                "/ai/classify",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"subject": subject, "description": description, "agency": agency}
            )
        )  # type: ignore

    def train_ai(self, access_token: str) -> dict[str, Any]:
        return self._json(self._request("POST", "/ai/train", headers={"Authorization": f"Bearer {access_token}"}))  # type: ignore

    def get_ticket_audit_logs(self, access_token: str, ticket_id: str) -> list[dict[str, Any]]:
        return self._json(self._request("GET", f"/tickets/{ticket_id}/audit", headers={"Authorization": f"Bearer {access_token}"}))  # type: ignore

    def list_interventions(self, access_token: str, ticket_id: str) -> list[dict[str, Any]]:
        return self._json(self._request("GET", f"/tickets/{ticket_id}/interventions", headers={"Authorization": f"Bearer {access_token}"}))  # type: ignore

    def create_intervention(self, access_token: str, ticket_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json(self._request("POST", f"/tickets/{ticket_id}/interventions", headers={"Authorization": f"Bearer {access_token}"}, json=payload))  # type: ignore

    def update_intervention(self, access_token: str, intervention_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json(self._request("PATCH", f"/interventions/{intervention_id}", headers={"Authorization": f"Bearer {access_token}"}, json=payload))  # type: ignore

    def review_intervention(self, access_token: str, intervention_id: str, decision: str, feedback: str = "") -> dict[str, Any]:
        return self._json(self._request("POST", f"/interventions/{intervention_id}/review", headers={"Authorization": f"Bearer {access_token}"}, json={"decision": decision, "feedback": feedback}))  # type: ignore

    def validate_ticket(self, access_token: str, ticket_id: str) -> dict[str, Any]:
        return self._json(self._request("POST", f"/tickets/{ticket_id}/validate", headers={"Authorization": f"Bearer {access_token}"}))  # type: ignore


