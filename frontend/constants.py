from __future__ import annotations

APP_TITLE = "ID Colis Support App"
BACKEND_URL = "http://localhost:8000"

NAVY = "#102A43"
BLUE = "#2F80ED"
GREEN = "#4B8E37"
YELLOW = "#D9A441"
RED = "#D64545"
ORANGE = "#E67E22"
SLATE = "#F0F4F8"
TEXT = "#102A43"
SOFT_BLUE = "#EAF2FF"
SOFT_GREEN = "#E6F4EA"
SOFT_YELLOW = "#FFF5D6"
SOFT_RED = "#FDE8E8"

AGENCY_STATIONS = {
    "Global Voyages": ["Bafoussam >> Douala", "Bafoussam >> Yaoundé", "Biyem-Assi", "DLA-Bépanda", "DLA-Brazzaville", "DLA-Mboppi", "DLA-Village", "Douala Akwa"],
    "Trésor Voyages": ["Bafoussam", "Baneghang", "DLA-Bépanda", "DLA-Bonabéri", "DLA-Brazzaville", "DLA-Village", "Dschang", "Mvan 2"],
}

DEMO_AGENT_NAMES = [
    "Support IT", "Aline Kamga", "Boris Tchana", "Clarisse Ndomo", "Didier Foka",
    "Estelle Mvondo", "Franck Tamba", "Grace Ngu", "Hervé Mballa", "Irene Njoya",
    "Junior Ebong", "Kevin Meka", "Laure Mbianda", "Mireille Nono", "Nadia Fotso",
    "Olivier Toko", "Prisca Muna", "Rosine Abena", "Serge Biloa", "Thérèse Etoa",
    "Ulrich Nsame", "Valérie Kenne", "Wilfried Momo",
]

USER_PAGES = [
    ("Accueil", "user_home"),
    ("Nouveau ticket", "ticket_create"),
    ("Mes tickets", "user_tickets"),
]

AGENT_PAGES = [
    ("Tableau de bord", "agent_dashboard"),
    ("Agences et postes", "directory"),
    ("Nouveau ticket", "ticket_create"),
    ("Tous les tickets", "agent_queue"),
    ("Interventions terrain", "interventions"),
    ("Diagnostics système", "diagnostics"),
]



