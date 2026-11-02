# ID Colis Support App repository guide

## Purpose

This is the independent ID Colis Support App for IT and Digital Minds. It supports incident reporting, AI-assisted classification, tenant-separated IT queues, and field-intervention reports for Global Voyages and Trésor Voyages.

The SOCADEL project is not a dependency, submodule, or deployment target. Do not copy its runtime database, credentials, logs, or generated artifacts into this repository.

## Repository layout

| Path | Responsibility |
|---|---|
| `backend/` | FastAPI application, authentication, SQLAlchemy models, AI routing, services, and seed data |
| `frontend/` | Streamlit portal, agency-themed UI, API client, session state, and views |
| `database/` | MySQL-compatible schema and database notes |
| `docs/` | Operations, workflows, and repository documentation |
| `scripts/` | Repeatable seed and verification utilities |
| `installer/` | Windows installer documentation and Inno Setup configuration |

## Local development

1. Create a Python 3.12+ virtual environment.
2. Install dependencies from `requirements.txt` or with `python -m pip install -e .`.
3. Copy `.env.example` to `.env` and set a strong `IDCOLIS_JWT_SECRET`.
4. Start FastAPI on port 8000 and Streamlit on port 8501.
5. Run `python -m scripts.seed_current_tickets` only when refreshing local demo records.

The application defaults to a local SQLite runtime database for development. Configure `IDCOLIS_DATABASE_URL` with a MySQL SQLAlchemy URL for shared or production deployments.

## Data and tenant boundaries

Global Voyages and Trésor Voyages are separate tenants. Every support session has an agency scope. Directory entries, users, tickets, and interventions are filtered by that scope in backend services; hiding a page in Streamlit is not an authorization boundary.

The development directory contains eight locations per agency, two posts per location, 32 end-user assignments, and one support account. Demo passwords are for local testing only.

## Verification checklist

- `python -m compileall -q backend frontend scripts`
- `python scripts/test_agency_workflows.py`
- Verify `/api/health` returns HTTP 200.
- Log in through both agency routes and confirm tenant isolation.
- Create a ticket and verify category, priority, agency, and local location.
- Review AI suggestions as support IT.
- Create and save an intervention report.
- Confirm `.env`, databases, logs, uploads, and build output remain ignored.

## Git workflow

Use descriptive commits. Do not commit secrets or generated runtime data. Before pushing, inspect `git diff --cached` and `git status --short`. The repository has no remote configured by default; add the organization-approved remote explicitly before pushing online.
