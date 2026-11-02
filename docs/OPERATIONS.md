# ID Colis Support App Operations Guide

## Start the services

Run these commands from the repository root in separate PowerShell terminals:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -m streamlit run frontend\main.py --server.port 8501
```

Check availability:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health
Invoke-WebRequest http://127.0.0.1:8501
```

## Configuration and database

Copy `.env.example` to `.env`. Configure `IDCOLIS_DATABASE_URL`, `IDCOLIS_JWT_SECRET`, `IDCOLIS_API_URL`, and `IDCOLIS_CORS_ORIGINS`. SQLite is suitable for local demonstrations. Shared and production environments must use MySQL with `utf8mb4`, a restricted database account, HTTPS, and scheduled backups. Initialize the database with `database/schema.sql`.

## Refresh development data

```powershell
.\.venv\Scripts\python.exe -m scripts.seed_current_tickets
```

This development-only command replaces stale ticket activity with current tickets attached to the agency users and posts. It must not be used against production data.

## Troubleshooting

- Backend unavailable: verify port 8000 and `IDCOLIS_API_URL`.
- AI preview failure: inspect backend and frontend logs; the UI displays a safe error instead of a traceback.
- Wrong agency view: log out and re-enter through the correct agency card; backend tenant authorization remains authoritative.
- Missing local agency on an old ticket: tickets created before location metadata was enabled may not have a site. New tickets carry the selected location automatically.
