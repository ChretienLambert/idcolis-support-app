from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..auth.service import hash_password
from ..models import (
    AIPrediction,
    Agent,
    AuditLog,
    MockActiveDirectory,
    RefreshSession,
    Role,
    Team,
    Ticket,
    TicketComment,
    User,
    utcnow,
)


def reference_training_rows() -> list[dict[str, str]]:
    """Training dataset for ticket routing model (~100 examples across 4 teams)"""
    return [
        # identity-access: OUTLOOK (20 examples)
        {
            "subject": "Impossible d'accéder à Outlook",
            "description": "Mon compte email ne se synchronise plus et j'ai une erreur de connexion.",
            "category": "Outlook",
            "priority": "Élevée",
            "team_slug": "identity-access",
        },
        {
            "subject": "Erreur authentification Outlook",
            "description": "Je reçois 'impossible de se connecter' sur le client lourd. Outlook web fonctionne.",
            "category": "Outlook",
            "priority": "Élevée",
            "team_slug": "identity-access",
        },
        {
            "subject": "Boîte mail ne remplace pas",
            "description": "Les nouveaux emails n'apparaissent pas dans Outlook. Dernier message reçu il y a 2 heures.",
            "category": "Outlook",
            "priority": "Élevée",
            "team_slug": "identity-access",
        },
        {
            "subject": "Mot de passe email expiré",
            "description": "Outlook indique erreur 'motdepasse invalide'. J'ai réinitialiser 3 fois sans succès.",
            "category": "Outlook",
            "priority": "Élevée",
            "team_slug": "identity-access",
        },
        {
            "subject": "Impossible envoyer mails",
            "description": "Je peux lire mes mails mais impossible d'en envoyer. Code erreur SMTP.",
            "category": "Outlook",
            "priority": "Moyenne",
            "team_slug": "identity-access",
        },
        {
            "subject": "Conflit calendrier Outlook",
            "description": "Mon calendrier affiche des événements dupliqués et mon assistant agent virtuel ne répond plus.",
            "category": "Outlook",
            "priority": "Moyenne",
            "team_slug": "identity-access",
        },
        {
            "subject": "Outlook plantage répété",
            "description": "Outlook se crashes dès l'ouverture. Impossible de démarrer l'application.",
            "category": "Outlook",
            "priority": "Élevée",
            "team_slug": "identity-access",
        },
        {
            "subject": "Pièces jointes ne s'ouvrent pas",
            "description": "Je reçois des pièces jointes dans Outlook mais impossible de les ouvrir. Erreur permission.",
            "category": "Outlook",
            "priority": "Moyenne",
            "team_slug": "identity-access",
        },
        {
            "subject": "Configuration Outlook manquante",
            "description": "Nouvel ordinateur portable. Besoin de configurer mon compte email Outlook.",
            "category": "Outlook",
            "priority": "Moyenne",
            "team_slug": "identity-access",
        },
        {
            "subject": "Signature email disparue",
            "description": "Ma signature Outlook a disparu après mise à jour. Comment la retrouver?",
            "category": "Outlook",
            "priority": "Faible",
            "team_slug": "identity-access",
        },
        {
            "subject": "Données Outlook corrompues",
            "description": "Fichier OST semble corrompue. Tous les anciens emails ont disparu.",
            "category": "Outlook",
            "priority": "Élevée",
            "team_slug": "identity-access",
        },
        {
            "subject": "Login Office 365 bloqué",
            "description": "Impossible se connecter à Office 365 depuis mon poste. Authentification demande 2FA récurrent.",
            "category": "Outlook",
            "priority": "Élevée",
            "team_slug": "identity-access",
        },
        {
            "subject": "Dossier emails disparu",
            "description": "Mon dossier 'Projets' a disparu d'Outlook après synchronisation.",
            "category": "Outlook",
            "priority": "Élevée",
            "team_slug": "identity-access",
        },
        {
            "subject": "Règle Outlook ne fonctionne pas",
            "description": "Mes règles de tri automatique ne s'appliquent plus aux nouveaux emails.",
            "category": "Outlook",
            "priority": "Moyenne",
            "team_slug": "identity-access",
        },
        {
            "subject": "Outlook recherche lent",
            "description": "La recherche dans Outlook prend plus de 30 secondes pour trouver un email.",
            "category": "Outlook",
            "priority": "Moyenne",
            "team_slug": "identity-access",
        },
        {
            "subject": "Email bloqué spam",
            "description": "Un email important a été bloqué par le filtre spam. Comment le récupérer?",
            "category": "Outlook",
            "priority": "Moyenne",
            "team_slug": "identity-access",
        },
        {
            "subject": "Calendrier partagé inaccessible",
            "description": "Je ne peux plus voir le calendrier de mon équipe. Erreur permission.",
            "category": "Outlook",
            "priority": "Élevée",
            "team_slug": "identity-access",
        },
        {
            "subject": "Outlook hors ligne",
            "description": "Outlook reste en mode hors ligne même avec connexion internet active.",
            "category": "Outlook",
            "priority": "Élevée",
            "team_slug": "identity-access",
        },
        {
            "subject": "Réponse automatique défaillante",
            "description": "Mon message d'absence ne s'envoie pas automatiquement.",
            "category": "Outlook",
            "priority": "Moyenne",
            "team_slug": "identity-access",
        },
        {
            "subject": "Archive Outlook inaccessible",
            "description": "Impossible d'ouvrir les archives PST de l'année dernière.",
            "category": "Outlook",
            "priority": "Moyenne",
            "team_slug": "identity-access",
        },
        {
            "subject": "Contact Outlook dupliqué",
            "description": "Mes contacts apparaissent en double dans le carnet d'adresses.",
            "category": "Outlook",
            "priority": "Faible",
            "team_slug": "identity-access",
        },
        
        # network-connectivity (25 examples)
        {
            "subject": "VPN indisponible",
            "description": "Je ne peux pas me connecter au réseau de l'entreprise depuis l'extérieur.",
            "category": "Réseau",
            "priority": "Critique",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Connexion WiFi instable",
            "description": "Le WiFi se déconnecte toutes les 5 minutes. Routeur-01 dans la zone rouge.",
            "category": "Réseau",
            "priority": "Moyenne",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Pas d'accès réseau avec câble ethernet",
            "description": "Connecté au switch mais aucune IP attribuée. Port réseau sur mon PC semble bon.",
            "category": "Réseau",
            "priority": "Critique",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "VPN lent depuis le bureau",
            "description": "Quand je me connecte au VPN depuis home, téléchargement 2Mb/s. Normalement 50Mb/s.",
            "category": "Réseau",
            "priority": "Moyenne",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Impossible accéder serveur interne",
            "description": "Je ne peux pas ping le serveur 192.168.1.50. Erreur timeout.",
            "category": "Réseau",
            "priority": "Critique",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Routeur déconnecté",
            "description": "Routeur bâtiment C clignotant rouge. Tout le bâtiment sans internet.",
            "category": "Réseau",
            "priority": "Critique",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Problème LAN configuration",
            "description": "Configuration réseau locale changée. Besoin aide pour reconfigurer pont LAN.",
            "category": "Réseau",
            "priority": "Moyenne",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Firewall bloque accès",
            "description": "Essaie accéder base données mais firewall refuse le port. Quel port autoriser?",
            "category": "Réseau",
            "priority": "Élevée",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Switch réseau ne répond plus",
            "description": "Switch salle serveur ne répond plus à ping. Lumières OFF. Disjoncteur?",
            "category": "Réseau",
            "priority": "Critique",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Problème DNS résolution",
            "description": "Ne peut pas accéder intranet. Error: name resolution failed for intranet.idcolis.cm.",
            "category": "Réseau",
            "priority": "Élevée",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Bande passante saturée",
            "description": "Réseau très lent. Soupçonne un virus télécharge données massif.",
            "category": "Réseau",
            "priority": "Élevée",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Proxy authentication error",
            "description": "Navigateur demande authentification proxy en boucle. Credentials corrects.",
            "category": "Réseau",
            "priority": "Élevée",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "DHCP ne distribue pas d'IP",
            "description": "Postes nouveaux dans le service marketing n'obtiennent pas d'adresse IP.",
            "category": "Réseau",
            "priority": "Critique",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Portail captif bloqué",
            "description": "WiFi invités bloqués sur portail captif. Page ne se charge pas.",
            "category": "Réseau",
            "priority": "Moyenne",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "VLAN inaccessible",
            "description": "Impossible d'accéder au VLAN finance depuis mon poste.",
            "category": "Réseau",
            "priority": "Élevée",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "VPN certificate expired",
            "description": "Client VPN indique certificat expiré. Besoin renouvellement.",
            "category": "Réseau",
            "priority": "Critique",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "network-connectivity segment isolated",
            "description": "Sous-réseau R&D isolé du reste du réseau. Ping échoue.",
            "category": "Réseau",
            "priority": "Critique",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Load balancer error",
            "description": "Load balancer renvoie 502 errors intermittents sur application web.",
            "category": "Réseau",
            "priority": "Critique",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "IP address conflict",
            "description": "Message 'IP address conflict' sur plusieurs postes du même sous-réseau.",
            "category": "Réseau",
            "priority": "Élevée",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "VPN connection drops",
            "description": "VPN se déconnecte aléatoirement toutes les 10 minutes.",
            "category": "Réseau",
            "priority": "Élevée",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "network-connectivity printer offline",
            "description": "Imprimante réseau inaccessible depuis tous les postes.",
            "category": "Réseau",
            "priority": "Moyenne",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Subnet mask incorrect",
            "description": "Configuration sous-réseau incorrecte sur serveur de fichiers.",
            "category": "Réseau",
            "priority": "Élevée",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Gateway unreachable",
            "description": "Passerelle par défaut inaccessible depuis certains postes.",
            "category": "Réseau",
            "priority": "Critique",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "MAC address filtering",
            "description": "Poste bloqué par filtrage MAC sur le point d'accès WiFi.",
            "category": "Réseau",
            "priority": "Moyenne",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "network-connectivity latency high",
            "description": "Latence réseau > 200ms vers serveurs de production.",
            "category": "Réseau",
            "priority": "Élevée",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "Packet loss detected",
            "description": "15% de perte de paquets vers le datacenter principal.",
            "category": "Réseau",
            "priority": "Critique",
            "team_slug": "network-connectivity",
        },
        {
            "subject": "RDP connection failed",
            "description": "Impossible de se connecter en RDP aux serveurs Windows.",
            "category": "Réseau",
            "priority": "Élevée",
            "team_slug": "network-connectivity",
        },
        
        # waybill-sync (25 examples)
        {
            "subject": "Erreur sur l'application interne",
            "description": "L'application de gestion de congés ne charge pas correctement.",
            "category": "Logiciels",
            "priority": "Élevée",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "SharePoint inaccessible",
            "description": "Erreur 403 Forbidden en accédant au site SharePoint de mon équipe.",
            "category": "Logiciels",
            "priority": "Élevée",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Erreur 500 application métier",
            "description": "Portail ERP affiche 'Internal Server Error'. Base données connectée?",
            "category": "Logiciels",
            "priority": "Critique",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Base données lente",
            "description": "Requête SQL sur l'application de paie prend 10 minutes au lieu de 30 secondes.",
            "category": "Logiciels",
            "priority": "Élevée",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Logiciel ne démarre plus",
            "description": "Après mise à jour, l'application CRM ne démarre plus. Écran noir.",
            "category": "Logiciels",
            "priority": "Critique",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Accès application refusé",
            "description": "Reçu message 'Insufficient permissions' sur l'intranet. Besoin droits?",
            "category": "Logiciels",
            "priority": "Élevée",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Plugin navigateur manquant",
            "description": "Java plugin pour l'application web désactivé. Comment réactiver?",
            "category": "Logiciels",
            "priority": "Moyenne",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "CMS page ne sauvegarde pas",
            "description": "Quand je clique 'Save' sur le CMS, rien se passe. Pas message erreur.",
            "category": "Logiciels",
            "priority": "Élevée",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Application gelée",
            "description": "Application bureau Lotus freezes après 5 minutes d'utilisation.",
            "category": "Logiciels",
            "priority": "Moyenne",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Export données échoue",
            "description": "Impossible exporter rapport XLS depuis l'application. 'Export service unavailable'.",
            "category": "Logiciels",
            "priority": "Moyenne",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Compte application expiré",
            "description": "Message 'Your account has expired' dans l'application serveur. Renouvellement?",
            "category": "Logiciels",
            "priority": "Élevée",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Mise à jour application bloquée",
            "description": "L'application refuse de mettre à jour. Erreur permission administrateur.",
            "category": "Logiciels",
            "priority": "Moyenne",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "SAP transaction error",
            "description": "Transaction SAP échoue avec erreur 'No authorization'.",
            "category": "Logiciels",
            "priority": "Élevée",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Excel macro disabled",
            "description": "Macros Excel bloquées par sécurité. Comment autoriser?",
            "category": "Logiciels",
            "priority": "Moyenne",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Application timeout",
            "description": "Application web timeout après 30 secondes d'inactivité.",
            "category": "Logiciels",
            "priority": "Moyenne",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Database connection failed",
            "description": "Application ne peut plus se connecter à PostgreSQL. Connection refused.",
            "category": "Logiciels",
            "priority": "Critique",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "API rate limit exceeded",
            "description": "Application reçoit 429 Too Many Requests de l'API externe.",
            "category": "Logiciels",
            "priority": "Élevée",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "File upload failed",
            "description": "Impossible d'uploader fichiers > 10MB sur le portail document.",
            "category": "Logiciels",
            "priority": "Moyenne",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Application layout broken",
            "description": "Interface cassée après mise à jour Chrome. Elements décalés.",
            "category": "Logiciels",
            "priority": "Moyenne",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Synchronization error",
            "description": "Sync entre application mobile et desktop échoue.",
            "category": "Logiciels",
            "priority": "Élevée",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "License expired",
            "description": "Licence Adobe Creative Suite expirée. waybill-sync ne démarrent plus.",
            "category": "Logiciels",
            "priority": "Critique",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Memory leak application",
            "description": "Application consomme 4GB RAM après 1 heure d'utilisation.",
            "category": "Logiciels",
            "priority": "Élevée",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "PDF generation failed",
            "description": "Génération PDF échoue dans l'application de reporting.",
            "category": "Logiciels",
            "priority": "Moyenne",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Authentication token invalid",
            "description": "JWT token rejeté par l'API. Erreur 'Invalid signature'.",
            "category": "Logiciels",
            "priority": "Élevée",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Application crash on startup",
            "description": "Application Python crash immédiatement au démarrage. Stacktrace vide.",
            "category": "Logiciels",
            "priority": "Critique",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Data corruption detected",
            "description": "Application détecte corruption dans fichier de données local.",
            "category": "Logiciels",
            "priority": "Critique",
            "team_slug": "waybill-sync",
        },
        {
            "subject": "Integration broken",
            "description": "Intégration Salesforce-ERP ne synchronise plus les données.",
            "category": "Logiciels",
            "priority": "Critique",
            "team_slug": "waybill-sync",
        },
        
        # scanning-hardware (30 examples)
        {
            "subject": "Imprimante ne répond plus",
            "description": "La photocopieuse réseau affiche une erreur et n'imprime plus.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "PC ne démarre plus",
            "description": "Ordinateur portable ne s'allume plus. Batterie chargée, aucun son.",
            "category": "Matériel",
            "priority": "Critique",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Écran externe ne fonctionne pas",
            "description": "Connecté moniteur USB-C mais pas détecté. Paramètre affichage?",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Clavier/souris sans réponse",
            "description": "Clavier Bluetooth se déconnecte. Souris USB ne bouge plus.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Écran bleu BSOD",
            "description": "PC affiche écran bleu avec erreur 0x0000007E.",
            "category": "Matériel",
            "priority": "Critique",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Ventilateur PC bruyant",
            "description": "Ventilateur fonctionne à 100% toute la journée. Très bruyant.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Disque dur plein",
            "description": "Disque C: 99% rempli. PC très lent maintenant.",
            "category": "Matériel",
            "priority": "Élevée",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Batterie laptop vide rapide",
            "description": "Batterie se décharge en 1 heure même avec alimentation optimisée.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Cartouche imprimante vide",
            "description": "Imprimante de bureau affiche 'Cartouche vide'. Besoin de fournitures?",
            "category": "Matériel",
            "priority": "Faible",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Port USB ne reconnaît pas périphérique",
            "description": "Clé USB 32GB non détectée sur port USB-A. Essayé 3 ports différents.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Moniteur flou ou vibrant",
            "description": "Écran affiche image flou avec petites vibrations. Après reboot, pareil.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Webcam ne détecte pas visage",
            "description": "Webcam portable détectée mais vidéo noire ou gelée dans Teams.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "RAM defect detected",
            "description": "Memtest indique erreurs sur barrette RAM slot 2.",
            "category": "Matériel",
            "priority": "Élevée",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "SSD slow performance",
            "description": "Disque SSD très lent. Benchmark montre 10MB/s au lieu de 500MB/s.",
            "category": "Matériel",
            "priority": "Élevée",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Overheating laptop",
            "description": "Portable surchauffe après 30 minutes d'utilisation. CPU 90°C.",
            "category": "Matériel",
            "priority": "Élevée",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Docking station not working",
            "description": "Station d'accueil ne détecte ni moniteurs ni périphériques USB.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Scanner paper jam",
            "description": "Scanner multifonction bourrage papier à chaque passage.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Headset microphone not working",
            "description": "Micro casque USB non détecté dans Teams. Audio fonctionne.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Server power supply failed",
            "description": "Alimentation serveur grillée. Serveur éteint brusquement.",
            "category": "Matériel",
            "priority": "Critique",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "RAID array degraded",
            "description": "Contrôleur RAID indique array dégradé. Disque 2 défaillant.",
            "category": "Matériel",
            "priority": "Critique",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "UPS battery low",
            "description": "Onduleur batterie faible. Remplacement nécessaire.",
            "category": "Matériel",
            "priority": "Élevée",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Graphics card artifacts",
            "description": "Carte graphique affiche artefacts colorés sur écran.",
            "category": "Matériel",
            "priority": "Élevée",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Motherboard capacitor leak",
            "description": "Condensateurs gonflés sur carte mère. Instabilité système.",
            "category": "Matériel",
            "priority": "Critique",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "network-connectivity card not detected",
            "description": "Carte réseau non reconnue par Windows après mise à jour pilote.",
            "category": "Matériel",
            "priority": "Élevée",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Projector lamp replacement",
            "description": "Projecteur salle réunion lampe grillée. Image sombre.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Tablet touch screen unresponsive",
            "description": "Écran tactile tablette ne répond plus. Boutons physiques OK.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "External hard drive not mounting",
            "description": "Disque dur externe USB 3.0 non détecté. Bruit mécanique.",
            "category": "Matériel",
            "priority": "Élevée",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Smart card reader error",
            "description": "Lecteur carte à puce ne lit plus les badges d'accès.",
            "category": "Matériel",
            "priority": "Élevée",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Biometric scanner failed",
            "description": "Scanner empreinte digitale ne reconnaît plus les doigts enregistrés.",
            "category": "Matériel",
            "priority": "Moyenne",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Server rack cooling issue",
            "description": "Température armoire serveur excessive. Climatisation défaillante.",
            "category": "Matériel",
            "priority": "Critique",
            "team_slug": "scanning-hardware",
        },
        {
            "subject": "Tape drive backup failed",
            "description": "Sauvegarde sur bande échouée. Lecteur bande erreur mécanique.",
            "category": "Matériel",
            "priority": "Élevée",
            "team_slug": "scanning-hardware",
        },
    ]


def cleanse_activity_data(db: Session) -> None:
    """Delete all ticket-related data and sessions while keeping Users, Roles, Teams, and Agents."""
    db.execute(delete(TicketComment))
    db.execute(delete(AIPrediction))
    db.execute(delete(Ticket))
    db.execute(delete(AuditLog))
    db.execute(delete(RefreshSession))
    db.commit()


def ensure_demo_data(db: Session) -> None:
    """Ensure demo users, roles, teams and agents exist without deleting ticket history."""
    role_values = {
        "Utilisateur": "Utilisateur final",
        "Support_IT": "Agent support IT",
    }
    existing_roles = {role.name: role for role in db.execute(select(Role)).scalars().all()}
    for name, description in role_values.items():
        if name not in existing_roles:
            role = Role(name=name, description=description)
            db.add(role)
            existing_roles[name] = role
    db.commit()

    teams_data = [
        {
            "name": "ID Colis accès et support",
            "slug": "identity-access",
            "description": "Support helpdesk et assistance applicative.",
            "default_queue": "Helpdesk",
        },
        {
            "name": "Connectivité agences",
            "slug": "network-connectivity",
            "description": "Support réseau et connectivité.",
            "default_queue": "Réseau",
        },
        {
            "name": "Support waybill-sync",
            "slug": "waybill-sync",
            "description": "Assistance sur les logiciels et waybill-sync métiers.",
            "default_queue": "waybill-sync",
        },
        {
            "name": "Scanners et équipements",
            "slug": "scanning-hardware",
            "description": "Scanners et équipements et périphériques.",
            "default_queue": "Matériel",
        },
        {
            "name": "Flotte et application chauffeur",
            "slug": "fleet-driver",
            "description": "Support des chauffeurs et des applications de flotte.",
            "default_queue": "Flotte",
        },
    ]
    existing_teams = {team.slug: team for team in db.execute(select(Team)).scalars().all()}
    for team_data in teams_data:
        if team_data["slug"] not in existing_teams:
            team = Team(**team_data)
            db.add(team)
            existing_teams[team.slug] = team
    db.commit()

    def ensure_user(email: str, full_name: str, role_name: str, password: str) -> User:
        stmt = select(User).where(User.email == email.lower().strip())
        user = db.execute(stmt).scalar_one_or_none()
        role = existing_roles[role_name]
        if not user:
            user = User(
                email=email.lower().strip(),
                full_name=full_name,
                password_hash=hash_password(password),
                role_id=role.id,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    clients = [
        {
            "email": "jean.dupont@idcolis.cm",
            "full_name": "Jean Dupont",
            "role": "Utilisateur",
            "password": "IDColis2024!",
        }
    ]
    for user_data in clients:
        ensure_user(user_data["email"], user_data["full_name"], user_data["role"], user_data["password"])

    agents = [
        {"email": "support@idcolis.cm", "full_name": "Support IT", "team_slug": "identity-access", "password": "Support123!"},
    ]
    for agent_data in agents:
        user = ensure_user(agent_data["email"], agent_data["full_name"], "Support_IT", agent_data["password"])
        team = existing_teams[agent_data["team_slug"]]
        existing_agent = db.execute(select(Agent).where(Agent.user_id == user.id)).scalar_one_or_none()
        if not existing_agent:
            db.add(Agent(user_id=user.id, team_id=team.id, title=team.name, is_primary=True, is_active=True))
    db.commit()

    # Seed Mock Active Directory and 10 mock users
    mock_ad_data = [
        {"email": "jean.dupont@idcolis.cm", "full_name": "Jean Dupont", "region": "Centre", "department": "Logistique"},
        {"email": "marie.linga@idcolis.cm", "full_name": "Marie Linga", "region": "Littoral", "department": "Ventes"},
        {"email": "paul.atangana@idcolis.cm", "full_name": "Paul Atangana", "region": "Est", "department": "Production"},
        {"email": "alice.fotso@idcolis.cm", "full_name": "Alice Fotso", "region": "Ouest", "department": "RH"},
        {"email": "hamadou.bello@idcolis.cm", "full_name": "Hamadou Bello", "region": "Adamaoua", "department": "Finance"},
        {"email": "moussa.ibrahim@idcolis.cm", "full_name": "Moussa Ibrahim", "region": "Nord", "department": "Sécurité"},
        {"email": "fadimatou.sali@idcolis.cm", "full_name": "Fadimatou Sali", "region": "Extrême-Nord", "department": "Communication"},
        {"email": "samuel.eboa@idcolis.cm", "full_name": "Samuel Eboa", "region": "Sud", "department": "Maintenance"},
        {"email": "john.tanyi@idcolis.cm", "full_name": "John Tanyi", "region": "Sud-Ouest", "department": "Informatique"},
        {"email": "emmanuel.fon@idcolis.cm", "full_name": "Emmanuel Fon", "region": "Nord-Ouest", "department": "Qualité"},
    ]

    for data in mock_ad_data:
        # Ensure in Mock AD table
        stmt_ad = select(MockActiveDirectory).where(MockActiveDirectory.email == data["email"])
        mock_entry = db.execute(stmt_ad).scalar_one_or_none()
        if not mock_entry:
            mock_entry = MockActiveDirectory(
                email=data["email"],
                region=data["region"],
                department=data["department"]
            )
            db.add(mock_entry)

        # Ensure as a User in the system
        stmt_user = select(User).where(User.email == data["email"])
        user = db.execute(stmt_user).scalar_one_or_none()
        if not user:
            user = User(
                email=data["email"],
                full_name=data["full_name"],
                password_hash=hash_password("IDColis2024!"),
                role_id=existing_roles["Utilisateur"].id,
                is_active=True,
                region=data["region"],
                department=data["department"]
            )
            db.add(user)
    db.commit()

    from sqlalchemy import func
    def create_initial_ticket(email: str, subject: str, description: str):
        stmt = select(User).where(User.email == email)
        user = db.execute(stmt).scalar_one_or_none()
        if not user: return

        stmt_tkt = select(Ticket).where(Ticket.requester_user_id == user.id, Ticket.subject == subject)
        if db.execute(stmt_tkt).scalar_one_or_none(): return

        count = db.execute(select(func.count()).select_from(Ticket)).scalar_one()
        tkt_id = f"TKT-2026-{count + 1:05d}"

        ticket = Ticket(
            id=tkt_id,
            requester_user_id=user.id,
            created_by_user_id=user.id,
            subject=subject,
            description=description,
            category="Autre",
            priority="Moyenne",
            status="En attente",
            team_id=db.execute(select(Team).where(Team.slug == "identity-access")).scalar_one().id,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(ticket)
        db.commit()

    initial_tickets = [
        {"email": "jean.dupont@idcolis.cm", "subject": "Synchronisation Outlook - Centre", "description": "Mes emails ne se chargent plus au siège à Yaoundé."},
        {"email": "marie.linga@idcolis.cm", "subject": "Accès VPN - Littoral", "description": "Connexion impossible depuis Douala."},
        {"email": "alice.fotso@idcolis.cm", "subject": "Imprimante - Ouest", "description": "L'imprimante de Bafoussam est hors ligne."},
        {"email": "paul.atangana@idcolis.cm", "subject": "Lenteur ERP - Est", "description": "Application très lente depuis Bertoua."},
    ]

    for tkt in initial_tickets:
        create_initial_ticket(tkt["email"], tkt["subject"], tkt["description"])


def seed_demo_data(db: Session) -> None:
    # Keep training data (AIPrediction) and sessions (RefreshSession). Remove all ticket data, users, teams, agents.
    for model in (TicketComment, Ticket, AuditLog, Agent, User, Team, Role):
        db.execute(delete(model))
    db.commit()

    role_values = {
        "Utilisateur": "Utilisateur final",
        "Support_IT": "Agent support IT",
    }
    existing_roles = {role.name: role for role in db.execute(select(Role)).scalars().all()}
    for name, description in role_values.items():
        if name not in existing_roles:
            role = Role(name=name, description=description)
            db.add(role)
            existing_roles[name] = role
    db.commit()

    teams_data = [
        {
            "name": "ID Colis accès et support",
            "slug": "identity-access",
            "description": "Support helpdesk et assistance applicative.",
            "default_queue": "Helpdesk",
        },
        {
            "name": "Connectivité agences",
            "slug": "network-connectivity",
            "description": "Support réseau et connectivité.",
            "default_queue": "Réseau",
        },
        {
            "name": "Support waybill-sync",
            "slug": "waybill-sync",
            "description": "Assistance sur les logiciels et waybill-sync métiers.",
            "default_queue": "waybill-sync",
        },
        {
            "name": "Scanners et équipements",
            "slug": "scanning-hardware",
            "description": "Scanners et équipements et périphériques.",
            "default_queue": "Matériel",
        },
        {
            "name": "Flotte et application chauffeur",
            "slug": "fleet-driver",
            "description": "Support des chauffeurs et des applications de flotte.",
            "default_queue": "Flotte",
        },
    ]
    existing_teams = {team.slug: team for team in db.execute(select(Team)).scalars().all()}
    for team_data in teams_data:
        if team_data["slug"] not in existing_teams:
            team = Team(**team_data)
            db.add(team)
            existing_teams[team.slug] = team
    db.commit()

    def ensure_user(email: str, full_name: str, role_name: str, password: str) -> User:
        stmt = select(User).where(User.email == email.lower().strip())
        user = db.execute(stmt).scalar_one_or_none()
        role = existing_roles[role_name]
        if not user:
            user = User(
                email=email.lower().strip(),
                full_name=full_name,
                password_hash=hash_password(password),
                role_id=role.id,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    clients = [
        {
            "email": "jean.dupont@idcolis.cm",
            "full_name": "Jean Dupont",
            "role": "Utilisateur",
            "password": "IDColis2024!",
        }
    ]
    for user_data in clients:
        ensure_user(user_data["email"], user_data["full_name"], user_data["role"], user_data["password"])

    agents = [
        {"email": "support@idcolis.cm", "full_name": "Support IT", "team_slug": "identity-access", "password": "Support123!"},
    ]
    for agent_data in agents:
        user = ensure_user(agent_data["email"], agent_data["full_name"], "Support_IT", agent_data["password"])
        team = existing_teams[agent_data["team_slug"]]
        existing_agent = db.execute(select(Agent).where(Agent.user_id == user.id)).scalar_one_or_none()
        if not existing_agent:
            db.add(Agent(user_id=user.id, team_id=team.id, title=team.name, is_primary=True, is_active=True))
    db.commit()

    # Seed Mock Active Directory and 10 mock users
    mock_ad_data = [
        {"email": "jean.dupont@idcolis.cm", "full_name": "Jean Dupont", "region": "Centre", "department": "Logistique"},
        {"email": "marie.linga@idcolis.cm", "full_name": "Marie Linga", "region": "Littoral", "department": "Ventes"},
        {"email": "paul.atangana@idcolis.cm", "full_name": "Paul Atangana", "region": "Est", "department": "Production"},
        {"email": "alice.fotso@idcolis.cm", "full_name": "Alice Fotso", "region": "Ouest", "department": "RH"},
        {"email": "hamadou.bello@idcolis.cm", "full_name": "Hamadou Bello", "region": "Adamaoua", "department": "Finance"},
        {"email": "moussa.ibrahim@idcolis.cm", "full_name": "Moussa Ibrahim", "region": "Nord", "department": "Sécurité"},
        {"email": "fadimatou.sali@idcolis.cm", "full_name": "Fadimatou Sali", "region": "Extrême-Nord", "department": "Communication"},
        {"email": "samuel.eboa@idcolis.cm", "full_name": "Samuel Eboa", "region": "Sud", "department": "Maintenance"},
        {"email": "john.tanyi@idcolis.cm", "full_name": "John Tanyi", "region": "Sud-Ouest", "department": "Informatique"},
        {"email": "emmanuel.fon@idcolis.cm", "full_name": "Emmanuel Fon", "region": "Nord-Ouest", "department": "Qualité"},
    ]

    for data in mock_ad_data:
        # Ensure in Mock AD table
        stmt_ad = select(MockActiveDirectory).where(MockActiveDirectory.email == data["email"])
        mock_entry = db.execute(stmt_ad).scalar_one_or_none()
        if not mock_entry:
            mock_entry = MockActiveDirectory(
                email=data["email"],
                region=data["region"],
                department=data["department"]
            )
            db.add(mock_entry)

        # Ensure as a User in the system
        stmt_user = select(User).where(User.email == data["email"])
        user = db.execute(stmt_user).scalar_one_or_none()
        if not user:
            user = User(
                email=data["email"],
                full_name=data["full_name"],
                password_hash=hash_password("IDColis2024!"),
                role_id=existing_roles["Utilisateur"].id,
                is_active=True,
                region=data["region"],
                department=data["department"]
            )
            db.add(user)
    db.commit()

    from sqlalchemy import func
    def create_initial_ticket(email: str, subject: str, description: str):
        stmt = select(User).where(User.email == email)
        user = db.execute(stmt).scalar_one_or_none()
        if not user: return

        stmt_tkt = select(Ticket).where(Ticket.requester_user_id == user.id, Ticket.subject == subject)
        if db.execute(stmt_tkt).scalar_one_or_none(): return

        count = db.execute(select(func.count()).select_from(Ticket)).scalar_one()
        tkt_id = f"TKT-2026-{count + 1:05d}"

        ticket = Ticket(
            id=tkt_id,
            requester_user_id=user.id,
            created_by_user_id=user.id,
            subject=subject,
            description=description,
            category="Autre",
            priority="Moyenne",
            status="En attente",
            team_id=db.execute(select(Team).where(Team.slug == "identity-access")).scalar_one().id,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(ticket)
        db.commit()

    initial_tickets = [
        {"email": "jean.dupont@idcolis.cm", "subject": "Synchronisation Outlook - Centre", "description": "Mes emails ne se chargent plus au siège à Yaoundé."},
        {"email": "marie.linga@idcolis.cm", "subject": "Accès VPN - Littoral", "description": "Connexion impossible depuis Douala."},
        {"email": "alice.fotso@idcolis.cm", "subject": "Imprimante - Ouest", "description": "L'imprimante de Bafoussam est hors ligne."},
        {"email": "paul.atangana@idcolis.cm", "subject": "Lenteur ERP - Est", "description": "Application très lente depuis Bertoua."},
    ]

    for tkt in initial_tickets:
        create_initial_ticket(tkt["email"], tkt["subject"], tkt["description"])



