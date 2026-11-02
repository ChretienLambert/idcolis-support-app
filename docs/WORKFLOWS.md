# Tested ID Colis Workflows

## Global Voyages

1. Select Global Voyages, a local agency, and an assigned end user.
2. Confirm account selection fills the login form without returning to agency selection.
3. Submit a slow-computer incident describing an old HP computer and slow ID Colis pages.
4. Log in through the Global IT route and confirm the ticket appears in the Global queue only.
5. Review the AI suggestion, send a support response, and move the ticket to `En cours`.

Tested ticket: `TKT-2026-00019`. Result: `Matériel`, priority `Élevée`.

## Trésor Voyages

The same workflow was tested through Trésor Voyages with a Trésor location and end user. Tested ticket: `TKT-2026-00020`. Result: `Matériel`, priority `Élevée`. The Trésor IT session remained isolated from Global Voyages.

## Field intervention

For the Global ticket, the IT agent opened `Interventions terrain` and completed diagnosis, actions performed, affected HP computer, tests, result, follow-up, and technician notes. The report was saved as `INT-2026-00001` with result `Partiellement résolu`.

Expected lifecycle:

`En attente` → AI review → IT response → `En cours` → intervention report → `Résolu` or follow-up.

Ticket discussion and audit logs record the important actions.
