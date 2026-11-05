from __future__ import annotations

from datetime import UTC, timedelta

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai.model import Prediction, TicketRoutingModel
from ..seed.demo import reference_training_rows
from ..models import AIPrediction, Agent, AuditLog, Team, Ticket, TicketComment, User, UserAgency, utcnow

RESOLVED_STATUSES = {"Résolu", "Clôturé"}
OPEN_STATUSES = {"Créé", "Assigné", "En attente", "En cours", "En attente de validation", "À corriger"}


class TicketService:
    def __init__(self, db: Session, classifier: TicketRoutingModel) -> None:
        self.db = db
        self.classifier = classifier

    def _agent_for_user(self, user_id: str) -> Agent | None:
        return self.db.execute(select(Agent).where(Agent.user_id == user_id, Agent.is_active.is_(True))).scalar_one_or_none()

    def _ensure_ticket_access(self, ticket: Ticket, user: User) -> None:
        if user.role.name == "Utilisateur":
            if ticket.requester_user_id != user.id:
                raise PermissionError("Forbidden")
            return

        if user.role.name in {"Support_IT", "Régulateur_Agence"}:
            tenant = getattr(user, "_agency_scope", None)
            if user.role.name == "Régulateur_Agence" and not tenant:
                assignment = self.db.execute(select(UserAgency).where(UserAgency.user_id == user.id)).scalar_one_or_none()
                tenant = assignment.agency if assignment else None
            if tenant and ticket.agency != tenant:
                raise PermissionError("This ticket belongs to another agency.")
            return

        raise PermissionError("Forbidden")

    def _ticket_number(self) -> str:
        count = self.db.execute(select(func.count()).select_from(Ticket)).scalar_one()
        return f"TKT-2026-{count + 1:05d}"

    def _team_by_slug(self, slug: str) -> Team:
        slug = {
            "helpdesk-core": "identity-access",
            "network": "network-connectivity",
            "applications": "waybill-sync",
            "hardware": "scanning-hardware",
        }.get(slug, slug)
        team = self.db.execute(select(Team).where(Team.slug == slug)).scalar_one_or_none()
        if not team:
            raise ValueError(f"Team not found: {slug}")
        return team

    def _primary_agent_for_team(self, team_id: str) -> Agent | None:
        agent = self.db.execute(
            select(Agent).where(Agent.team_id == team_id, Agent.is_active.is_(True), Agent.is_primary.is_(True))
        ).scalar_one_or_none()
        if agent:
            return agent
        return self.db.execute(select(Agent).where(Agent.team_id == team_id, Agent.is_active.is_(True))).scalars().first()

    def _record_prediction(self, ticket: Ticket, prediction: Prediction, agent: Agent | None) -> AIPrediction:
        entry = AIPrediction(
            ticket_id=ticket.id,
            model_name=self.classifier.model_name,
            category=prediction.category,
            priority=prediction.priority,
            team_id=ticket.team_id,
            agent_id=agent.id if agent else None,
            confidence=prediction.confidence,
            features_json={"notes": prediction.notes},
        )
        self.db.add(entry)
        return entry

    def _audit(self, actor_user_id: str | None, entity_type: str, entity_id: str, action: str, payload: dict) -> None:
        self.db.add(
            AuditLog(
                actor_user_id=actor_user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                payload_json=payload,
            )
        )

    def list_tickets(self, user: User, priority: str | None = None, status: str | None = None, agency: str | None = None) -> list[Ticket]:
        stmt = select(Ticket).order_by(Ticket.created_at.desc())
        if user.role.name == "Utilisateur":
            stmt = stmt.where(Ticket.requester_user_id == user.id)
        elif user.role.name in {"Support_IT", "Régulateur_Agence"}:
            tenant = getattr(user, "_agency_scope", None)
            if user.role.name == "Régulateur_Agence" and not tenant:
                assignment = self.db.execute(select(UserAgency).where(UserAgency.user_id == user.id)).scalar_one_or_none()
                tenant = assignment.agency if assignment else None
            if tenant:
                stmt = stmt.where(Ticket.agency == tenant)
        else:
            return []
        if priority:
            stmt = stmt.where(Ticket.priority == priority)
        # Regulators receive the complete agency queue by default. Their view
        # must include untouched tickets as well as tickets already handled by IT.
        if status and user.role.name != "Régulateur_Agence":
            stmt = stmt.where(Ticket.status == status)
        if agency:
            stmt = stmt.where(Ticket.agency == agency)
        return list(self.db.execute(stmt).scalars().all())

    def get_ticket(self, ticket_id: str, user: User | None = None) -> Ticket:
        ticket = self.db.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError("Ticket not found.")
        if user is not None:
            self._ensure_ticket_access(ticket, user)
        return ticket

    def create_ticket(self, requester_user_id: str, subject: str, description: str, created_by_user_id: str | None = None, metadata: dict | None = None) -> Ticket:
        requester = self.db.get(User, requester_user_id)
        if not requester:
            raise ValueError("Requester not found.")
        prediction = self.classifier.predict(subject, description, (metadata or {}).get("agency"))
        team = self._team_by_slug(prediction.team_slug)
        primary_agent = self._primary_agent_for_team(team.id)
        ticket = Ticket(
            id=self._ticket_number(),
            requester_user_id=requester_user_id,
            created_by_user_id=created_by_user_id or requester_user_id,
            subject=subject,
            description=description,
            agency=(metadata or {}).get("agency"),
            site=(metadata or {}).get("site"),
            city=(metadata or {}).get("city"),
            operational_impact=(metadata or {}).get("operational_impact", "Individuel"),
            field_intervention_required=(metadata or {}).get("field_intervention_required", False),
            category=prediction.category,
            priority=prediction.priority,
            status="Créé",
            service_concerne=None,
            team_id=team.id,
            assigned_agent_id=primary_agent.id if primary_agent else None,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        ticket.comments.append(
            TicketComment(
                author_user_id=requester_user_id,
                author_role=requester.role.name,
                body="Ticket créé par le portail utilisateur.",
                is_internal=False,
            )
        )
        self.db.add(ticket)
        self._record_prediction(ticket, prediction, primary_agent)
        self._audit(created_by_user_id, "Ticket", ticket.id, "created", {"subject": subject, "description": description})
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def get_training_data(self) -> list[dict[str, str]]:
        """Combine static reference data with dynamic data from the database."""
        db_rows = [
            {
                "subject": t.subject,
                "description": t.description,
                "category": t.category,
                "priority": t.priority,
                "team_slug": t.team.slug,
            }
            for t in self.db.execute(select(Ticket).join(Team).where(Ticket.status != "En attente")).scalars().all()
        ]
        return reference_training_rows() + db_rows

    def approve_ai_suggestions(self, ticket_id: str, agent_user_id: str, category: str, priority: str, team_slug: str, corrected: bool = False, service_concerne: str | None = None) -> Ticket:
        ticket = self.get_ticket(ticket_id)
        agent = self.db.get(User, agent_user_id)
        if agent is not None:
            self._ensure_ticket_access(ticket, agent)
        if ticket.status not in {"Créé", "En attente"}:
            raise ValueError("Only newly created or pending tickets can be approved.")
        
        team = self._team_by_slug(team_slug)
        agent_profile = self._agent_for_user(agent_user_id)
        
        ticket.category = category
        ticket.priority = priority
        ticket.service_concerne = service_concerne or team.name
        ticket.team_id = team.id
        ticket.assigned_agent_id = agent_profile.id if agent_profile else None
        ticket.status = "Assigné"
        ticket.updated_at = utcnow()
        
        # Record AI prediction
        prediction = self.classifier.predict(ticket.subject, ticket.description)
        self._record_prediction(ticket, prediction, agent_profile)
        
        # If agent corrected AI, retrain the model with the full updated dataset
        if corrected:
            training_data = self.get_training_data()
            self.classifier.train(training_data)
        
        # Enhanced audit log with before/after values when corrections are made
        audit_payload = {
            "category": category,
            "priority": priority,
            "team": team.name,
            "corrected": corrected,
            "status": "Assigné",
        }
        
        if corrected:
            audit_payload.update({
                "ai_suggested_category": prediction.category,
                "ai_suggested_priority": prediction.priority,
                "ai_suggested_team": prediction.team_slug,
                "agent_modified_category": category,
                "agent_modified_priority": priority,
                "agent_modified_team": team_slug,
            })
        
        self._audit(agent_user_id, "Ticket", ticket.id, "approved_ai_suggestions", audit_payload)
        
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def add_comment(self, ticket_id: str, author_user_id: str, author_role: str, body: str, is_internal: bool = False) -> TicketComment:
        ticket = self.get_ticket(ticket_id)
        author = self.db.get(User, author_user_id)
        if author is not None:
            self._ensure_ticket_access(ticket, author)
        comment = TicketComment(ticket_id=ticket.id, author_user_id=author_user_id, author_role=author_role, body=body, is_internal=is_internal)
        ticket.updated_at = utcnow()
        self.db.add(comment)
        self._audit(author_user_id, "TicketComment", ticket.id, "comment_added", {"internal": is_internal})
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def change_status(self, ticket_id: str, status_value: str, actor_user_id: str | None = None) -> Ticket:
        ticket = self.get_ticket(ticket_id)
        actor = self.db.get(User, actor_user_id) if actor_user_id else None
        if actor is not None:
            self._ensure_ticket_access(ticket, actor)
        allowed_statuses = {
            "Créé", "Assigné", "En attente", "En cours",
            "En attente de validation", "À corriger", "Résolu", "Clôturé",
        }
        if status_value not in allowed_statuses:
            raise ValueError("Invalid ticket status.")
        if ticket.status == "Clôturé":
            raise ValueError("Closed tickets cannot be modified.")
        ticket.status = status_value
        ticket.updated_at = utcnow()
        if status_value in {"Résolu", "Clôturé"}:
            ticket.resolved_at = ticket.resolved_at or utcnow()
        self._audit(actor_user_id, "Ticket", ticket.id, "status_changed", {"status": status_value})
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def update_ticket(self, ticket_id: str, payload: dict, actor_user_id: str | None = None, actor_role: str | None = None) -> Ticket:
        ticket = self.get_ticket(ticket_id)
        actor = self.db.get(User, actor_user_id) if actor_user_id else None
        if actor is not None:
            self._ensure_ticket_access(ticket, actor)
        if ticket.status == "Clôturé":
            raise ValueError("Closed tickets cannot be modified.")
        if ticket.status == "Résolu" and actor_role == "Utilisateur":
            raise ValueError("Resolved tickets cannot be edited by users.")
        for key in ["subject", "description", "status"]:
            if key in payload and payload[key] is not None:
                setattr(ticket, key, payload[key])
        if ticket.status in {"Résolu", "Clôturé"}:
            ticket.resolved_at = ticket.resolved_at or utcnow()
        ticket.updated_at = utcnow()
        self._audit(actor_user_id, "Ticket", ticket.id, "updated", payload)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def assign_ticket(self, ticket_id: str, to_team_id: str | None = None, to_agent_id: str | None = None, reason: str = "", actor_user_id: str | None = None) -> Ticket:
        ticket = self.get_ticket(ticket_id)
        actor = self.db.get(User, actor_user_id) if actor_user_id else None
        if actor is not None:
            self._ensure_ticket_access(ticket, actor)
        if to_team_id:
            ticket.team_id = to_team_id
        if to_agent_id:
            ticket.assigned_agent_id = to_agent_id
        ticket.updated_at = utcnow()
        self._audit(actor_user_id, "Ticket", ticket.id, "assigned", {"team_id": to_team_id, "agent_id": to_agent_id, "reason": reason})
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def find_similar_tickets(self, ticket: Ticket, limit: int = 3, threshold: float = 0.35) -> tuple[list[tuple[Ticket, float]], list[tuple[Ticket, float]]]:
        """Compare a ticket's text against others in the same agency using
        TF-IDF cosine similarity, to flag likely duplicates among open
        tickets and surface already-resolved tickets with a similar fix."""
        candidates = list(
            self.db.execute(
                select(Ticket).where(Ticket.agency == ticket.agency, Ticket.id != ticket.id)
            ).scalars().all()
        )
        if not candidates:
            return [], []
        corpus = [f"{t.subject} {t.description}" for t in candidates]
        corpus.append(f"{ticket.subject} {ticket.description}")
        vectors = TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words=None).fit_transform(corpus)
        scores = cosine_similarity(vectors[-1], vectors[:-1])[0]
        scored = [(candidates[i], float(scores[i])) for i in range(len(candidates)) if scores[i] >= threshold]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        duplicates = [pair for pair in scored if pair[0].status in OPEN_STATUSES][:limit]
        resolved = [pair for pair in scored if pair[0].status in RESOLVED_STATUSES][:limit]
        return duplicates, resolved

    def recurring_issues(self, agency: str | None = None, days: int = 30, min_count: int = 3) -> list[dict]:
        """Group recent tickets by (agency, site, category) to surface a
        problem that keeps coming back instead of being fixed once."""
        since = utcnow() - timedelta(days=days)
        stmt = select(Ticket).where(Ticket.created_at >= since)
        if agency:
            stmt = stmt.where(Ticket.agency == agency)
        tickets = list(self.db.execute(stmt).scalars().all())
        groups: dict[tuple[str | None, str | None, str], list[Ticket]] = {}
        for t in tickets:
            key = (t.agency, t.site, t.category)
            groups.setdefault(key, []).append(t)
        results = []
        for (agency_name, site, category), items in groups.items():
            if len(items) < min_count:
                continue
            latest = max(items, key=lambda t: t.created_at)
            results.append(
                {
                    "agency": agency_name,
                    "site": site,
                    "category": category,
                    "count": len(items),
                    "latest_ticket_id": latest.id,
                    "latest_created_at": latest.created_at,
                }
            )
        results.sort(key=lambda row: row["count"], reverse=True)
        return results

    def ai_performance(self) -> dict:
        """Summarize how often agents accept the AI's suggestion as-is versus
        correct it, using the audit trail already written by
        approve_ai_suggestions (no extra tracking table needed)."""
        logs = list(
            self.db.execute(
                select(AuditLog).where(AuditLog.action == "approved_ai_suggestions").order_by(AuditLog.created_at.desc())
            ).scalars().all()
        )
        total = len(logs)
        corrected = sum(1 for log in logs if log.payload_json.get("corrected"))
        accepted = total - corrected
        recent_corrections = [
            {
                "ticket_id": log.entity_id,
                "ai_suggested_category": log.payload_json.get("ai_suggested_category"),
                "agent_modified_category": log.payload_json.get("agent_modified_category"),
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
            if log.payload_json.get("corrected")
        ][:5]
        acceptance_rate = round((accepted / total) * 100, 1) if total else 0.0
        return {
            "total_decisions": total,
            "accepted": accepted,
            "corrected": corrected,
            "acceptance_rate": acceptance_rate,
            "recent_corrections": recent_corrections,
        }

    def connectivity_risk_tickets(self, agency: str | None = None, hours: int = 24) -> list[dict]:
        """Flag Network/Connectivity tickets that have stayed unresolved past
        the threshold. The ID Colis app itself runs offline, so a station
        without connectivity for this long isn't just inconvenienced — it
        likely isn't syncing or backing up its work, which needs a human
        follow-up call, not just another ticket in the queue."""
        threshold = (utcnow() - timedelta(hours=hours)).replace(tzinfo=None)
        stmt = select(Ticket).where(
            Ticket.category == "Network / Connectivity",
            Ticket.status.not_in(RESOLVED_STATUSES),
            Ticket.created_at <= threshold,
        )
        if agency:
            stmt = stmt.where(Ticket.agency == agency)
        tickets = list(self.db.execute(stmt).scalars().all())
        results = []
        now = utcnow()
        for ticket in tickets:
            created_at = ticket.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            hours_open = (now - created_at).total_seconds() / 3600
            results.append(
                {
                    "ticket_id": ticket.id,
                    "subject": ticket.subject,
                    "agency": ticket.agency,
                    "site": ticket.site,
                    "status": ticket.status,
                    "hours_open": round(hours_open, 1),
                    "created_at": ticket.created_at,
                }
            )
        results.sort(key=lambda row: row["hours_open"], reverse=True)
        return results


