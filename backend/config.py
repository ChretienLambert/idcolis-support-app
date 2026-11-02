from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
STORAGE_DIR = BACKEND_DIR / "storage"
MODEL_DIR = STORAGE_DIR / "models"


@dataclass(frozen=True)
class Settings:
    app_name: str = "ID Colis Support App API"
    env: str = os.getenv("IDCOLIS_ENV", "development")
    database_url: str = os.getenv(
        "IDCOLIS_DATABASE_URL",
        os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'demo_runtime.db'}"),
    )
    jwt_secret: str = os.getenv("IDCOLIS_JWT_SECRET", "idcolis-dev-secret-change-me-please-use-a-longer-key")
    jwt_algorithm: str = os.getenv("IDCOLIS_JWT_ALGORITHM", "HS256")
    access_token_minutes: int = int(os.getenv("IDCOLIS_ACCESS_TOKEN_MINUTES", "15"))
    refresh_token_days: int = int(os.getenv("IDCOLIS_REFRESH_TOKEN_DAYS", "7"))
    session_days: int = int(os.getenv("IDCOLIS_SESSION_DAYS", "30"))
    frontend_base_url: str = os.getenv("IDCOLIS_FRONTEND_URL", "http://localhost:8501")
    cors_origins: str = os.getenv("IDCOLIS_CORS_ORIGINS", frontend_base_url)
    upload_dir: str = os.getenv("IDCOLIS_UPLOAD_DIR", str(STORAGE_DIR / "uploads"))

    def ensure_paths(self) -> None:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_paths()


