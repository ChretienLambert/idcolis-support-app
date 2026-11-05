# ID Colis Support App

Support and field-intervention management for ID Colis operations at IT and Digital Minds.

The application receives incidents from agencies such as Trésor Voyages and Global Voyages, uses a local AI classifier to suggest category, priority, and routing, and gives technicians a structured online intervention report.

See `docs/OPERATIONS.md` for setup, configuration, database, and troubleshooting instructions. See `docs/WORKFLOWS.md` for the complete tested user-to-IT and field-intervention workflows. See `docs/REPOSITORY.md` for the repository layout, Git workflow, release checklist, and deployment boundaries.

## Installation

Create the MySQL database using `database/schema.sql`, copy `.env.example` to `.env`, and set `IDCOLIS_DATABASE_URL` and `IDCOLIS_JWT_SECRET`.

For a first local run, the project uses the local demo database. MySQL is the intended shared or production database. Copy `.env.example` to `.env` and configure `IDCOLIS_DATABASE_URL` and `IDCOLIS_JWT_SECRET` before deployment.

This project supports two installation methods:

### Method 1: Script-based Installation
See `setup.bat` and `docs/OPERATIONS.md` for installation using Python scripts and batch files.

### Method 2: Windows Installer (Inno Setup)
See `installer/INSTALLER_SETUP.md` for building a professional Windows installer wizard.

## Development

### Install as a package

1. Create a Python 3.12 virtual environment
2. Install the package:

```bash
python -m pip install --upgrade pip wheel
python -m pip install .
```

### Run the backend

```bash
python -m backend.serve
```

The backend listens on `http://127.0.0.1:8000`. API routes are available under both the legacy internal paths and the documented `/api/...` prefix.

### Run the frontend

```bash
python -m streamlit run app.py
```

The frontend communicates with FastAPI and never connects directly to MySQL. Run the backend and frontend in separate terminals.

## Tenant separation

Global Voyages and Trésor Voyages are separate support tenants. The backend binds every authenticated support session to the agency selected at login. Directory entries, users, tickets, and interventions are filtered by that agency, and users cannot authenticate through the other agency route.

## Demo data

The development seed creates 8 locations per agency, 2 posts per location, 32 agency users, one IT support account, and current logistics tickets. Replace demo credentials before deployment. The current ticket seed can be refreshed with:

```powershell
python -m scripts.seed_current_tickets
```

Never commit `.env`, database files, logs, uploaded evidence, model artifacts, or `.venv`.

### Build a wheel package

```bash
python -m pip install build
python -m build
```

The built wheel will appear in the `dist/` folder.

## Project Structure

```
.
├── app.py                 # Main frontend entry point
├── requirements.txt       # Python dependencies
├── setup.py              # Package setup configuration
├── backend/              # FastAPI backend
│   ├── app.py
│   ├── serve.py
│   ├── ai/
│   ├── auth/
│   ├── db/
│   ├── models/
│   └── services/
├── frontend/             # Streamlit frontend
│   ├── app.py
│   ├── pages/
│   ├── services/
│   └── views/
├── install-scripts/      # Script-based installation
│   ├── DEPLOYMENT.md
│   ├── clean.bat
│   └── clean-venv.bat
└── installer/            # Windows installer (Inno Setup)
    ├── INSTALLER_SETUP.md
    ├── build_installer.bat
    ├── package_exe.bat
    ├── launcher.py
    └── IDColisSetup.iss
```

## Git and release hygiene

The repository must not include `.env`, local databases, logs, uploaded evidence, virtual environments, generated build output, or installer artifacts. Before committing, run `python -m compileall -q backend frontend scripts`, `python scripts/test_agency_workflows.py`, and inspect `git status --short`.
