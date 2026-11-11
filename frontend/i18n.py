from __future__ import annotations

from typing import Any

import streamlit as st

LANGUAGES = ("fr", "en")


def get_lang() -> str:
    return st.session_state.get("lang", "fr")


def sync_lang_from_query() -> None:
    """The URL carries the language so it survives reloads, logins and logouts."""
    try:
        lang = st.query_params.get("lang")
    except Exception:
        lang = None
    if lang in LANGUAGES:
        st.session_state.lang = lang
    st.session_state.setdefault("lang", "fr")


def t(text: Any, **kwargs: Any) -> Any:
    """French is the source text; unknown strings and non-strings pass through unchanged."""
    if not isinstance(text, str):
        return text
    if get_lang() == "en":
        text = EN.get(text, text)
    return text.format(**kwargs) if kwargs else text


def lang_key(key: str) -> str:
    """Widget key for a dropdown whose labels are translated.

    Streamlit keeps showing a keyed selectbox's current value in the old
    language after a switch, so each language gets its own widget.
    """
    return f"{key}__{get_lang()}"


def language_switch() -> None:
    """One language button pinned to the top-left corner on every page."""
    target = "en" if get_lang() == "fr" else "fr"
    label = "🌐 EN" if target == "en" else "🌐 FR"
    with st.container(key="idc-lang-switch"):
        st.markdown(
        """
        <style>
        .st-key-idc-lang-switch { position: fixed !important; top: .55rem; left: .75rem; z-index: 1000002; width: auto !important; }
        .st-key-idc-lang-switch button {
            width: auto !important; min-height: 0 !important; padding: .3rem .85rem !important;
            border-radius: 999px !important; background: #FFFFFF !important; color: #102A43 !important;
            border: 1px solid #DCE5EC !important; box-shadow: 0 4px 14px rgba(16,42,67,.12) !important;
        }
        section[data-testid="stSidebar"] > div:first-child { padding-top: 2.2rem; }
        .st-key-idc-lang-switch [data-testid="stElementContainer"]:has(style) { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
        )
        if st.button(label, key="idc_lang_button", help="English" if target == "en" else "Français"):
            st.session_state.lang = target
            try:
                st.query_params["lang"] = target
            except Exception:
                pass
            st.rerun()


EN: dict[str, str] = {
    # Navigation and roles
    "Accueil": "Home",
    "Nouveau ticket": "New ticket",
    "Mes tickets": "My tickets",
    "Tableau de bord": "Dashboard",
    "Agences et postes": "Agencies & posts",
    "Tous les tickets": "All tickets",
    "Interventions terrain": "Field interventions",
    "Diagnostics système": "System diagnostics",
    "Tickets à valider": "Tickets to validate",
    "Déconnexion": "Log out",
    "Opérations": "Operations",
    "Administration": "Administration",
    "Support terrain et logistique": "Field & logistics support",
    "Agent Support IT": "IT Support agent",
    "Régulateur agence": "Agency regulator",
    "Utilisateur final": "End user",
    "Utilisateur": "User",
    "Support_IT": "IT Support",
    "Régulateur_Agence": "Agency regulator",

    # Ticket statuses
    "Créé": "Created",
    "Assigné": "Assigned",
    "En attente": "Pending",
    "En cours": "In progress",
    "En attente de validation": "Awaiting validation",
    "À corriger": "Needs correction",
    "Résolu": "Resolved",
    "Clôturé": "Closed",
    "Approuvée": "Approved",

    # Intervention results
    "Suspendu": "Suspended",
    "Brouillon": "Draft",
    "Partiellement résolu": "Partially resolved",
    "Non résolu": "Not resolved",
    "Escaladé": "Escalated",

    # Priorities and categories
    "Faible": "Low",
    "Moyenne": "Medium",
    "Élevée": "High",
    "Critique": "Critical",
    "Autres": "Other",

    # Teams
    "ID Colis accès et support": "ID Colis access & support",
    "Connectivité agences": "Agency connectivity",
    "Support waybill-sync": "Waybill-sync support",
    "Scanners et équipements": "Scanners & equipment",
    "Flotte et application chauffeur": "Fleet & driver app",

    # Directory posts
    "Vente / dépôt": "Sales / drop-off",
    "Expédition / retrait": "Shipping / pick-up",

    # Filters
    "Tous": "All",
    "Toutes": "All",
    "Aujourd’hui": "Today",
    "7 derniers jours": "Last 7 days",
    "30 derniers jours": "Last 30 days",
    "Période": "Period",
    "Recherche": "Search",
    "Statut": "Status",
    "Priorité": "Priority",
    "Catégorie": "Category",
    "Sujet, ID...": "Subject, ID...",

    # Login
    "Choisissez votre agence": "Choose your agency",
    "Un espace de support adapté à votre réseau ID Colis.": "A support space tailored to your ID Colis network.",
    "Support terrain {agency}": "{agency} field support",
    "Continuer avec {agency}": "Continue with {agency}",
    "← Retour aux agences": "← Back to agencies",
    "Connexion": "Log in",
    "{agency} · espace support": "{agency} · support space",
    "Choisissez votre agence locale": "Choose your local agency",
    "Sélectionnez l'agence où vous travaillez pour continuer.": "Select the agency where you work to continue.",
    "Agence locale": "Local agency",
    "Choisir une agence": "Choose an agency",
    "Continuer vers la connexion": "Continue to login",
    "Support {agency}": "{agency} support",
    "Accédez à vos tickets, interventions terrain et demandes de support.": "Access your tickets, field interventions and support requests.",
    "Connexion {agency}": "{agency} login",
    "Agence locale : {site}": "Local agency: {site}",
    "Choisir un compte de test": "Choose a test account",
    "Compte de l’agence": "Agency account",
    "Choisir un compte": "Choose an account",
    "Nom de l’agent": "Agent name",
    "Mot de passe": "Password",
    "Compte Support IT": "IT Support account",
    "Saisissez le nom de l’agent.": "Enter the agent name.",
    "Saisissez votre mot de passe.": "Enter your password.",

    # User home and tickets
    "Espace utilisateur": "User space",
    "Filtrer mes tickets": "Filter my tickets",
    "Demandes créées": "Requests created",
    "Actifs": "Active",
    "Tickets ouverts et en cours": "Open and in-progress tickets",
    "Résolus": "Resolved",
    "Tickets clôturés": "Closed tickets",
    "Derniers tickets": "Latest tickets",
    "Aucun ticket pour le moment.": "No tickets yet.",
    "Suivi personnel": "Personal follow-up",
    "Aucun ticket ne correspond à ces filtres.": "No ticket matches these filters.",
    "Retour": "Back",

    # Ticket creation
    "Création de demande de support": "Create a support request",
    "Informations générales": "General information",
    "Sujet": "Subject",
    "Description détaillée": "Detailed description",
    "Description": "Description",
    "Caractères: {count}/2000": "Characters: {count}/2000",
    "Description un peu courte : précisez par exemple l'appareil concerné, depuis quand, et ce qui s'affiche à l'écran. Cela aide l'équipe à traiter votre ticket plus vite.": "The description is a bit short: mention for example the device involved, since when, and what is shown on screen. This helps the team handle your ticket faster.",
    "Vérifier une solution rapide": "Check for a quick fix",
    "Essayez ces étapes avant de créer un ticket — cela résout souvent le problème en quelques minutes.": "Try these steps before creating a ticket — they often fix the problem in a few minutes.",
    "C'est résolu, merci": "It's fixed, thanks",
    "Toujours un problème, créer le ticket": "Still a problem, create the ticket",
    "Annuler": "Cancel",
    "Créer le ticket": "Create ticket",
    "Ticket créé avec succès. Statut: En attente.": "Ticket created successfully. Status: Pending.",
    "Étape 1/3 : Informations générales": "Step 1/3: General information",
    "Étape 2/3 : Classification IA": "Step 2/3: AI classification",
    "Étape 3/3 : Confirmation": "Step 3/3: Confirmation",
    "Suivant →": "Next →",
    "← Précédent": "← Previous",
    "Suggestions générées par le modèle. Vérifiez et ajustez si nécessaire avant de valider.": "Suggestions generated by the model. Check and adjust if needed before confirming.",
    "Suggestions IA basées sur l’origine et le contenu": "AI suggestions based on origin and content",
    "Provenance détectée:": "Detected origin:",
    "Service concerné:": "Service involved:",
    "Inconnue": "Unknown",
    "Inconnu": "Unknown",
    "Catégorie suggérée": "Suggested category",
    "Priorité suggérée": "Suggested priority",
    "Équipe cible": "Target team",
    "Impossible d'obtenir les suggestions IA.": "Could not get AI suggestions.",
    "Résumé du ticket": "Ticket summary",
    "Équipe": "Team",
    "Ticket créé et routé vers l'équipe.": "Ticket created and routed to the team.",

    # Self-help articles (content comes from the backend in French)
    "Pas de connexion Internet ou Wi-Fi": "No Internet or Wi-Fi connection",
    "Vérifiez que le Wi-Fi est activé sur l'appareil (icône réseau dans la barre de tâches).": "Check that Wi-Fi is turned on on the device (network icon in the taskbar).",
    "Désactivez puis réactivez le Wi-Fi, ou débranchez/rebranchez le câble réseau.": "Turn Wi-Fi off and on again, or unplug and replug the network cable.",
    "Redémarrez la box ou le routeur de l'agence (éteindre 10 secondes, puis rallumer).": "Restart the agency's box or router (turn off for 10 seconds, then back on).",
    "Si un mot de passe Wi-Fi est demandé, vérifiez qu'il n'a pas été changé récemment.": "If a Wi-Fi password is requested, check that it hasn't been changed recently.",
    "Essayez d'ouvrir un autre site pour confirmer si le problème touche tout le réseau.": "Try opening another website to confirm whether the whole network is affected.",
    "L'application ID Colis ne se met pas à jour": "The ID Colis app won't update",
    "Fermez complètement l'application puis rouvrez-la.": "Close the app completely, then reopen it.",
    "Vérifiez votre connexion Internet (une mise à jour nécessite une connexion stable).": "Check your Internet connection (an update needs a stable connection).",
    "Redémarrez l'appareil (ordinateur, scanner ou téléphone).": "Restart the device (computer, scanner or phone).",
    "Si une mise à jour manuelle est proposée dans les paramètres de l'application, lancez-la.": "If a manual update is offered in the app settings, run it.",
    "Patientez quelques minutes : certaines mises à jour se déploient progressivement par agence.": "Wait a few minutes: some updates roll out gradually by agency.",
    "Mot de passe oublié ou compte bloqué": "Forgotten password or locked account",
    "Vérifiez que la touche Verr. Maj. (Caps Lock) n'est pas activée en saisissant le mot de passe.": "Make sure Caps Lock is off when typing the password.",
    "Essayez de vous reconnecter après une courte pause : un blocage temporaire se lève parfois seul après quelques minutes.": "Try logging in again after a short break: a temporary lock sometimes clears by itself after a few minutes.",
    "Si vous connaissez votre mot de passe mais qu'il est refusé, vérifiez qu'il n'y a pas d'espace invisible copié avec.": "If you know your password but it's refused, check that no invisible space was copied with it.",
    "Si le compte reste bloqué, un agent IT doit réinitialiser l'accès : créez un ticket pour que cela soit traité rapidement.": "If the account stays locked, an IT agent must reset access: create a ticket so it's handled quickly.",
    "L'imprimante ne répond pas": "The printer isn't responding",
    "Vérifiez que l'imprimante est allumée et que le câble (ou le Wi-Fi) est bien connecté.": "Check that the printer is on and the cable (or Wi-Fi) is connected.",
    "Vérifiez qu'il reste du papier et que le bac n'est pas bloqué.": "Check that there's paper left and the tray isn't jammed.",
    "Éteignez puis rallumez l'imprimante.": "Turn the printer off and on again.",
    "Relancez l'impression depuis le début (annulez les documents bloqués dans la file d'attente si besoin).": "Restart printing from the beginning (cancel documents stuck in the queue if needed).",
    "Le scanner ne lit pas les codes": "The scanner won't read codes",
    "Vérifiez que le scanner est bien branché ou que sa batterie n'est pas déchargée.": "Check that the scanner is plugged in or its battery isn't flat.",
    "Nettoyez la vitre de lecture avec un chiffon doux et sec.": "Clean the reading window with a soft, dry cloth.",
    "Essayez de scanner un autre code-barres pour vérifier si le problème est général ou lié à une seule étiquette.": "Try scanning another barcode to check whether the problem is general or limited to one label.",
    "Redémarrez le scanner (éteindre/rallumer, ou le reconnecter au poste).": "Restart the scanner (turn off and on, or reconnect it to the workstation).",

    # Agent dashboard and queue
    "Vue agent": "Agent view",
    "**{count}** tickets au total": "**{count}** tickets in total",
    "Actualiser": "Refresh",
    "Aucun ticket trouvé pour la période sélectionnée.": "No tickets found for the selected period.",
    "À traiter": "To handle",
    "En traitement": "Being handled",
    "Clôturés": "Closed",
    "Tickets par équipe": "Tickets by team",
    "Tickets récents": "Recent tickets",
    "Non attribué": "Unassigned",
    "Interventions IT en attente de votre décision": "IT interventions awaiting your decision",
    "Tickets de l’agence": "Agency tickets",
    "Vue complète de tous les tickets de votre agence": "Full view of all your agency's tickets",
    "File opérationnelle": "Operational queue",
    "Ouvrir →": "Open →",

    # Ticket detail
    "Activité et échanges": "Activity & messages",
    "Aucune activité pour le moment.": "No activity yet.",
    "Ticket créé par le portail utilisateur.": "Ticket created from the user portal.",
    "Validation de la suggestion IA": "AI suggestion review",
    "Vérifiez la suggestion générée par le modèle avant de continuer. Votre décision permet aussi de réentraîner l’IA.": "Check the model's suggestion before continuing. Your decision is also used to retrain the AI.",
    "Fermer": "Close",
    "Confiance faible ({confidence}) — vérifiez attentivement avant de valider.": "Low confidence ({confidence}) — check carefully before confirming.",
    "Analyse ID Colis": "ID Colis analysis",
    "Catégorie logistique:": "Logistics category:",
    "Priorité opérationnelle:": "Operational priority:",
    "Équipe de routage:": "Routing team:",
    "Intervention terrain:": "Field intervention:",
    "À confirmer par l’agent selon l’impact et le matériel concerné": "To be confirmed by the agent based on impact and equipment involved",
    "Fiabilité et justification:": "Reliability and rationale:",
    "Analyse automatique": "Automatic analysis",
    "Ce ticket ressemble à d'autres tickets déjà ouverts pour cette agence — vérifiez qu'il ne s'agit pas d'un doublon.": "This ticket looks like other tickets already open for this agency — check that it isn't a duplicate.",
    "Tickets similaires déjà résolus (référence rapide)": "Similar tickets already resolved (quick reference)",
    "Accepter la suggestion": "Accept suggestion",
    "Suggestions IA acceptées. Ticket routé vers l'équipe et mis en cours.": "AI suggestions accepted. Ticket routed to the team and set in progress.",
    "Rejeter et corriger": "Reject and correct",
    "Corriger la classification": "Correct the classification",
    "Catégorie logistique": "Logistics category",
    "Priorité opérationnelle": "Operational priority",
    "Confirmer la correction": "Confirm correction",
    "Suggestion IA rejetée. Correction appliquée et IA réentraînée avec les nouvelles données.": "AI suggestion rejected. Correction applied and AI retrained with the new data.",
    "Journal d’audit": "Audit log",
    "Acteur ID:": "Actor ID:",
    "Système": "System",
    "Entité:": "Entity:",
    "Action:": "Action:",
    "Aucun journal d'audit disponible.": "No audit log available.",
    "Impossible de charger le journal d'audit.": "Could not load the audit log.",
    "Accès refusé pour ce ticket. Si votre session a expiré, reconnectez-vous ci-dessous.": "Access denied for this ticket. If your session has expired, log in again below.",
    "Email": "Email",
    "Se reconnecter": "Log in again",
    "Reconnecté avec succès.": "Logged in again successfully.",
    "Retour à la liste des tickets": "Back to ticket list",
    "Localisation non renseignée": "Location not provided",
    "← Retour à la file": "← Back to queue",
    "Résumé opérationnel": "Operational summary",
    "Demandeur": "Requester",
    "Agence": "Agency",
    "Non renseignée": "Not provided",
    "Non renseigné": "Not provided",
    "À qualifier": "To qualify",
    "À évaluer": "To assess",
    "Poste / agence locale": "Post / local agency",
    "Équipe assignée": "Assigned team",
    "Non attribuée": "Unassigned",
    "Description de l’incident": "Incident description",
    "Aucune description fournie.": "No description provided.",
    "Sauvegarder": "Save",
    "📄 Voir le rapport d’opération": "📄 View operation report",
    "Ticket clôturé. Les commentaires restent disponibles, mais aucune modification n'est autorisée.": "Ticket closed. Comments remain available, but no changes are allowed.",
    "Le régulateur a approuvé le rapport. Vérifiez avec le support que le problème est bien résolu, puis validez le ticket.": "The regulator approved the report. Check with support that the problem is really fixed, then validate the ticket.",
    "Valider que le problème est résolu": "Confirm the problem is fixed",
    "Gestion du ticket": "Ticket management",
    "Ticket clôturé : une nouvelle demande nécessite un nouveau ticket.": "Ticket closed: a new request needs a new ticket.",
    "Démarrer une intervention": "Start an intervention",
    "Validation du rapport d’intervention": "Intervention report review",
    "Aucun rapport d’intervention à valider.": "No intervention report to review.",
    " · {count} rapports identiques": " · {count} identical reports",
    "Date d'intervention : {date} · Dernière mise à jour {updated}": "Intervention date: {date} · Last updated {updated}",
    "Soumis {count} fois à l'identique, entre {first} et {last}.": "Submitted {count} times unchanged, between {first} and {last}.",
    "Intervenant / contact client": "Technician / client contact",
    "Diagnostic": "Diagnosis",
    "Travail réalisé": "Work performed",
    "Équipement concerné": "Equipment involved",
    "Tests effectués": "Tests performed",
    "Pièces / temps passé": "Parts / time spent",
    "Résultat": "Result",
    "Prochaine action": "Next action",
    "Notes du technicien": "Technician notes",
    "Retour précédent : {feedback}": "Previous feedback: {feedback}",
    "Retour du régulateur": "Regulator feedback",
    "Demander une correction": "Request a correction",
    "Approuver le rapport": "Approve report",
    "Corriger l’attribution IA": "Correct the AI assignment",
    "Réattribuez ce ticket si le modèle a choisi le mauvais département ou le mauvais agent.": "Reassign this ticket if the model picked the wrong department or agent.",
    "Département cible": "Target department",
    "Agent cible": "Target agent",
    "Aucun agent actif n'est disponible dans ce département.": "No active agent is available in this department.",
    "Motif de correction": "Reason for correction",
    "Ex: le ticket a été routé vers le mauvais département.": "E.g. the ticket was routed to the wrong department.",
    "Réattribuer": "Reassign",
    "Attribution corrigée avec succès.": "Assignment corrected successfully.",
    "Aucune équipe disponible pour la réattribution.": "No team available for reassignment.",

    # Interventions
    "Interventions": "Interventions",
    "Rapports liés aux tickets ID Colis": "Reports linked to ID Colis tickets",
    "Aucun ticket disponible pour créer une intervention.": "No ticket available to create an intervention.",
    "Les interventions sont toujours rattachées à un ticket.": "Interventions are always linked to a ticket.",
    "Retour régulateur : {feedback}": "Regulator feedback: {feedback}",
    "Aucune intervention": "No intervention",
    "Voir le ticket": "View ticket",
    "Retour à la liste des interventions": "Back to intervention list",
    "Agence : {agency} · Agence locale : {site}": "Agency: {agency} · Local agency: {site}",
    "Historique des interventions": "Intervention history",
    "Date d'intervention : {date} · Enregistrée le {created} · Mise à jour {updated}": "Intervention date: {date} · Recorded {created} · Updated {updated}",
    "Tests": "Tests",
    "Retour régulateur": "Regulator feedback",
    "Cette intervention est clôturée et ne peut plus être modifiée. Créez un nouveau ticket pour un nouveau problème.": "This intervention is closed and can no longer be changed. Create a new ticket for a new problem.",
    "Nouvelle intervention": "New intervention",
    "Générer un brouillon de rapport à partir du ticket": "Generate a draft report from the ticket",
    "le problème signalé": "the reported problem",
    "Incident de type « {category} » signalé le {date}.": "“{category}” incident reported on {date}.",
    "Description initiale du demandeur : {description}": "Requester's initial description: {description}",
    "Diagnostic sur place à compléter : vérification du matériel, des connexions et reproduction du problème avec l'utilisateur.": "On-site diagnosis to complete: check the equipment and connections, and reproduce the problem with the user.",
    "Fiche d'intervention maintenance": "Maintenance intervention form",
    "Date de l'intervention": "Intervention date",
    "Informations sur le client": "Client information",
    "Description de la demande initiale / du dysfonctionnement": "Initial request / malfunction description",
    "Diagnostic initial et détaillé": "Initial and detailed diagnosis",
    "Rapport d'intervention / difficultés rencontrées *(obligatoire : décrivez ce qui a été fait)": "Intervention report / difficulties encountered *(required: describe what was done)",
    "Systèmes, ordinateurs ou équipements concernés": "Systems, computers or equipment involved",
    "Temps passé": "Time spent",
    "Pièces de rechange et consommables": "Spare parts and consumables",
    "Suivi recommandé / prochaine action": "Recommended follow-up / next action",
    "Enregistrer le rapport": "Save report",
    "Le rapport d'intervention (ce qui a été fait) est obligatoire avant d'enregistrer.": "The intervention report (what was done) is required before saving.",
    "Rapport d’intervention enregistré avec succès.": "Intervention report saved successfully.",
    "Rapports existants": "Existing reports",

    # Directory
    "Agence sélectionnée": "Selected agency",
    "Annuaire opérationnel de {agency}.": "{agency} operational directory.",
    "Aucune station n'est encore enregistrée pour cette agence.": "No station is registered for this agency yet.",
    "{count} agence(s) dans la file {agency}. Chaque agence possède deux postes et seuls ses utilisateurs sont affichés.": "{count} agency(ies) in the {agency} queue. Each agency has two posts and only its users are shown.",
    "Contact station": "Station contact",
    "Poste à affecter": "Post to assign",
    "Voir les tickets": "View tickets",
    "Tickets de {name}": "{name}'s tickets",
    "Historique et suivi du poste sélectionné": "History and follow-up of the selected post",
    "Aucun ticket enregistré pour ce poste.": "No ticket recorded for this post.",

    # Diagnostics
    "État du backend et des services ID Colis": "Status of the backend and ID Colis services",
    "Backend disponible - environnement: {env}": "Backend available - environment: {env}",
    "inconnu": "unknown",
    "Backend indisponible: {error}": "Backend unavailable: {error}",
    "Agences possiblement hors ligne": "Agencies possibly offline",
    "Tickets réseau/connectivité ouverts depuis plus de 24h : l'application ID Colis fonctionne hors ligne, donc ce n'est pas juste un inconfort — l'agence risque de ne plus synchroniser ni sauvegarder son travail. Un appel direct vaut mieux qu'attendre que le ticket remonte seul.": "Network/connectivity tickets open for more than 24h: the ID Colis app works offline, so this isn't just an inconvenience — the agency may stop syncing or saving its work. A direct call is better than waiting for the ticket to surface.",
    "Aucune agence hors ligne depuis plus de 24h.": "No agency offline for more than 24h.",
    "{days} jour(s)": "{days} day(s)",
    "Agence inconnue": "Unknown agency",
    "{location} · ouvert depuis {duration} · statut : {status}": "{location} · open for {duration} · status: {status}",
    "Fiabilité des suggestions IA": "AI suggestion reliability",
    "Aucune décision enregistrée pour le moment.": "No decision recorded yet.",
    "Décisions enregistrées": "Recorded decisions",
    "Depuis le début": "Since the start",
    "Suggestions acceptées": "Accepted suggestions",
    "Validées telles quelles": "Accepted as-is",
    "Taux d'acceptation": "Acceptance rate",
    "{count} correction(s)": "{count} correction(s)",
    "Dernières corrections apportées par les agents": "Latest corrections made by agents",
    "Problèmes récurrents": "Recurring problems",
    "Agence / poste / catégorie avec au moins 3 tickets sur les 30 derniers jours — signe d'un problème sous-jacent à traiter plutôt que de fermer ticket après ticket.": "Agency / post / category with at least 3 tickets in the last 30 days — a sign of an underlying problem to fix rather than closing ticket after ticket.",
    "Aucun problème récurrent détecté sur la période.": "No recurring problem detected over the period.",
    "{location} · {count} tickets récents · dernier le {date}": "{location} · {count} recent tickets · latest on {date}",

    # Operation report
    "%d/%m/%Y à %H:%M": "%d/%m/%Y at %H:%M",
    "← Retour au ticket": "← Back to ticket",
    "Le rapport d'opération n'est disponible qu'une fois le ticket entièrement validé : intervention du technicien, approbation du régulateur, puis confirmation du demandeur.": "The operation report is only available once the ticket is fully validated: technician intervention, regulator approval, then requester confirmation.",
    "Rapport d'opération — ID Colis Support": "Operation report — ID Colis Support",
    "Ticket {id} · Généré le {date}": "Ticket {id} · Generated on {date}",
    "Ouvert le": "Opened on",
    "Résolu le": "Resolved on",
    "Description de l'incident": "Incident description",
    "Notes de résolution": "Resolution notes",
    "Détail de l'intervention — {number}": "Intervention details — {number}",
    "Signature": "Signature",
    "Technicien (exécution)": "Technician (execution)",
    "Régulateur (approbation)": "Regulator (approval)",
    "Demandeur (confirmation)": "Requester (confirmation)",
    "Intervention du {date}": "Intervention on {date}",
    "Approuvé le {date}": "Approved on {date}",
    "Confirmé le {date}": "Confirmed on {date}",
    "Validation à trois parties": "Three-party validation",
    "Cette opération a été réalisée, contrôlée et confirmée par les personnes suivantes.": "This operation was carried out, checked and confirmed by the following people.",
}
