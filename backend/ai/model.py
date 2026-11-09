from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ..config import MODEL_DIR


from ..seed.demo import reference_training_rows


@dataclass
class Prediction:
    category: str
    priority: str
    team_slug: str
    confidence: float
    notes: str


class TicketRoutingModel:
    def __init__(self) -> None:
        self.category_model: Pipeline | None = None
        self.priority_model: Pipeline | None = None
        self.team_model: Pipeline | None = None
        self.model_name = "idcolis-logistics-sklearn-baseline"
        self.keyword_rules = [
            {
                "team_slug": "identity-access",
                "category": "ID Colis Application",
                "priority": "Moyenne",
                "keywords": ["lent", "lenteur", "ralentit", "performance", "ancien ordinateur", "vieux ordinateur", "slow"],
                "notes": "ID Colis application performance routing.",
            },
            {
                "team_slug": "fleet-driver",
                "category": "Fleet / Driver App",
                "priority": "Élevée",
                "keywords": ["driver", "chauffeur", "fleet", "conducteur", "application chauffeur", "trajet", "course"],
                "notes": "Logistics fleet and driver application routing.",
            },
            {
                "team_slug": "waybill-sync",
                "category": "Waybill / Manifest Sync",
                "priority": "Critique",
                "keywords": ["waybill", "manifest", "bordereau", "manifeste", "synchronisation", "sync", "colis introuvable", "doublon"],
                "notes": "Waybill and manifest synchronization routing.",
            },
            {
                "team_slug": "identity-access",
                "category": "Account / Authentication",
                "priority": "Élevée",
                "keywords": ["compte", "connexion", "login", "mot de passe", "authentification", "bloqué", "password", "outlook", "email", "e-mail", "messagerie", "courriel", "boîte mail", "sharepoint"],
                "notes": "Identity and access routing.",
            },
            {
                "team_slug": "scanning-hardware",
                "category": "Scanning / Hardware",
                "priority": "Moyenne",
                "keywords": ["scanner", "scan", "lecteur", "imprimante", "terminal", "matériel", "hardware", "panne", "écran"],
                "notes": "Scanning and field hardware routing.",
            },
            {
                "team_slug": "network-connectivity",
                "category": "Network / Connectivity",
                "priority": "Élevée",
                "keywords": ["wifi", "wi-fi", "internet", "réseau", "vpn", "connexion réseau", "routeur"],
                "notes": "Connectivity routing.",
            },
        ]
        # Phrases that signal a wide-impact outage regardless of which team the
        # ticket routes to: these escalate priority on top of the base match
        # instead of replacing it, since the category/team guess is unaffected.
        self.urgency_phrases = [
            "toute l'agence", "toute l’agence", "tous les postes", "plus aucun poste",
            "personne ne peut", "plus rien ne fonctionne", "arret total", "arrêt total",
            "panne totale", "depuis ce matin", "depuis hier", "urgent", "en urgence",
        ]

    @staticmethod
    def _pipeline() -> Pipeline:
        return Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
                ("clf", LogisticRegression(max_iter=1200)),
            ]
        )

    def train(self, rows: list[dict]) -> int:
        texts = [f"{row['subject']} {row['description']}" for row in rows]
        self.category_model = self._pipeline().fit(texts, [row["category"] for row in rows])
        self.priority_model = self._pipeline().fit(texts, [row["priority"] for row in rows])
        self.team_model = self._pipeline().fit(texts, [row["team_slug"] for row in rows])
        self.save()
        return len(rows)

    def predict(self, subject: str, description: str, station: str | None = None) -> Prediction:
        """Classify a logistics incident, using the station as additional context."""
        station_context = station or ""
        text = f"{station_context} {subject} {description}"
        lowered = text.lower()

        # Always try keyword prediction first - it's more reliable for known patterns
        keyword_prediction = self._keyword_predict(lowered)
        if keyword_prediction:
            return self._apply_urgency_escalation(lowered, keyword_prediction)

        # Fallback to ML model if no keyword match
        if not self.category_model or not self.priority_model or not self.team_model:
            raise RuntimeError("Model not trained.")
        category_probs = self.category_model.predict_proba([text])[0]
        priority_probs = self.priority_model.predict_proba([text])[0]
        team_probs = self.team_model.predict_proba([text])[0]
        category = self.category_model.classes_[category_probs.argmax()]
        priority = self.priority_model.classes_[priority_probs.argmax()]
        team_slug = self.team_model.classes_[team_probs.argmax()]
        confidence = float(max(category_probs.max(), priority_probs.max(), team_probs.max()))
        if confidence < 0.45:
            prediction = Prediction(
                category="Autres",
                priority="Moyenne",
                team_slug="helpdesk-core",
                confidence=confidence,
                notes="Fallback rule triggered because the model confidence was low.",
            )
        else:
            prediction = Prediction(
                category=str(category),
                priority=str(priority),
                team_slug=str(team_slug),
                confidence=confidence,
                notes="scikit-learn routing model",
            )
        return self._apply_urgency_escalation(lowered, prediction)

    def _apply_urgency_escalation(self, lowered_text: str, prediction: Prediction) -> Prediction:
        if prediction.priority == "Critique":
            return prediction
        matched = next((phrase for phrase in self.urgency_phrases if phrase in lowered_text), None)
        if not matched:
            return prediction
        return Prediction(
            category=prediction.category,
            priority="Critique",
            team_slug=prediction.team_slug,
            confidence=max(prediction.confidence, 0.9),
            notes=f"{prediction.notes} | Priorité relevée à Critique: impact large signalé (« {matched} »).",
        )

    def _keyword_predict(self, lowered_text: str) -> Prediction | None:
        best_candidates: list[tuple[dict, int, int]] = []
        best_score = 0

        # High-priority keywords that should almost always win (specific services)
        priority_keywords = {"outlook", "vpn", "wifi", "wi-fi", "sharepoint", "erp", "sap"}

        for rule in self.keyword_rules:
            score = 0
            specificity = 0
            priority_bonus = 0

            for keyword in rule["keywords"]:
                if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", lowered_text):
                    score += 1
                    specificity += len(keyword)
                    if keyword in priority_keywords:
                        priority_bonus += 10 # Strong weight for specific services

            total_score = (score * 5) + priority_bonus

            if total_score == 0:
                continue
            if total_score > best_score:
                best_score = total_score
                best_candidates = [(rule, specificity, total_score)]
            elif total_score == best_score:
                best_candidates.append((rule, specificity, total_score))

        if not best_candidates:
            return None

        # Tie-breaker using specificity (length of matched keywords)
        if len(best_candidates) > 1:
            best_candidates.sort(key=lambda x: x[1], reverse=True)

        best_rule = best_candidates[0][0]
        confidence = min(0.98, 0.60 + (best_score * 0.05))
        return Prediction(
            category=best_rule["category"],
            priority=best_rule["priority"],
            team_slug=best_rule["team_slug"],
            confidence=confidence,
            notes=f"{best_rule['notes']} (Keyword Match Score: {best_score})",
        )

    def save(self) -> None:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "category_model": self.category_model,
                "priority_model": self.priority_model,
                "team_model": self.team_model,
                "model_name": self.model_name,
            },
            MODEL_DIR / "ticket_routing.joblib",
        )

    def load(self) -> bool:
        path = MODEL_DIR / "ticket_routing.joblib"
        if not path.exists():
            return False
        payload = joblib.load(path)
        self.category_model = payload["category_model"]
        self.priority_model = payload["priority_model"]
        self.team_model = payload["team_model"]
        self.model_name = payload.get("model_name", self.model_name)
        return True


