from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SelfHelpArticle:
    title: str
    steps: list[str]


class SelfHelpAdvisor:
    """Suggests quick fixes for common, low-complexity problems before a
    ticket is created, so the agent queue isn't flooded with issues the
    person could resolve themselves in under a minute."""

    def __init__(self) -> None:
        self.articles: list[tuple[list[str], SelfHelpArticle]] = [
            (
                ["wifi", "wi-fi", "internet", "pas de connexion", "pas de reseau", "pas de réseau", "réseau coupé", "reseau coupe"],
                SelfHelpArticle(
                    title="Pas de connexion Internet ou Wi-Fi",
                    steps=[
                        "Vérifiez que le Wi-Fi est activé sur l'appareil (icône réseau dans la barre de tâches).",
                        "Désactivez puis réactivez le Wi-Fi, ou débranchez/rebranchez le câble réseau.",
                        "Redémarrez la box ou le routeur de l'agence (éteindre 10 secondes, puis rallumer).",
                        "Si un mot de passe Wi-Fi est demandé, vérifiez qu'il n'a pas été changé récemment.",
                        "Essayez d'ouvrir un autre site pour confirmer si le problème touche tout le réseau.",
                    ],
                ),
            ),
            (
                ["mise a jour", "mise à jour", "ne se met pas a jour", "ne se met pas à jour", "update", "application pas a jour"],
                SelfHelpArticle(
                    title="L'application ID Colis ne se met pas à jour",
                    steps=[
                        "Fermez complètement l'application puis rouvrez-la.",
                        "Vérifiez votre connexion Internet (une mise à jour nécessite une connexion stable).",
                        "Redémarrez l'appareil (ordinateur, scanner ou téléphone).",
                        "Si une mise à jour manuelle est proposée dans les paramètres de l'application, lancez-la.",
                        "Patientez quelques minutes : certaines mises à jour se déploient progressivement par agence.",
                    ],
                ),
            ),
            (
                ["mot de passe oublie", "mot de passe oublié", "mot de passe perdu", "compte bloque", "compte bloqué"],
                SelfHelpArticle(
                    title="Mot de passe oublié ou compte bloqué",
                    steps=[
                        "Vérifiez que la touche Verr. Maj. (Caps Lock) n'est pas activée en saisissant le mot de passe.",
                        "Essayez de vous reconnecter après une courte pause : un blocage temporaire se lève parfois seul après quelques minutes.",
                        "Si vous connaissez votre mot de passe mais qu'il est refusé, vérifiez qu'il n'y a pas d'espace invisible copié avec.",
                        "Si le compte reste bloqué, un agent IT doit réinitialiser l'accès : créez un ticket pour que cela soit traité rapidement.",
                    ],
                ),
            ),
            (
                ["imprimante", "impossible d'imprimer", "n'imprime pas", "imprimante hors ligne"],
                SelfHelpArticle(
                    title="L'imprimante ne répond pas",
                    steps=[
                        "Vérifiez que l'imprimante est allumée et que le câble (ou le Wi-Fi) est bien connecté.",
                        "Vérifiez qu'il reste du papier et que le bac n'est pas bloqué.",
                        "Éteignez puis rallumez l'imprimante.",
                        "Relancez l'impression depuis le début (annulez les documents bloqués dans la file d'attente si besoin).",
                    ],
                ),
            ),
            (
                ["scanner", "lecteur code barre", "lecteur code-barre", "scan ne fonctionne pas"],
                SelfHelpArticle(
                    title="Le scanner ne lit pas les codes",
                    steps=[
                        "Vérifiez que le scanner est bien branché ou que sa batterie n'est pas déchargée.",
                        "Nettoyez la vitre de lecture avec un chiffon doux et sec.",
                        "Essayez de scanner un autre code-barres pour vérifier si le problème est général ou lié à une seule étiquette.",
                        "Redémarrez le scanner (éteindre/rallumer, ou le reconnecter au poste).",
                    ],
                ),
            ),
        ]

    def suggest(self, subject: str, description: str) -> SelfHelpArticle | None:
        text = f"{subject} {description}".lower()
        for keywords, article in self.articles:
            if any(keyword in text for keyword in keywords):
                return article
        return None
