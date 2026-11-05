from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db.base import Base
from .db.session import SessionLocal, engine
from .dependencies import classifier
from .routers import ai, auth, catalog, directory, health, interventions, tickets
from .startup import run_startup_tasks

# Re-exported for scripts/tests that construct demo data directly.
from .seed.demo import ensure_demo_data, reference_training_rows  # noqa: F401


app = FastAPI(title=settings.app_name, version="0.1.0")
allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_login_attempts: dict[str, deque[float]] = defaultdict(deque)
_LOGIN_WINDOW_SECONDS = 60
_LOGIN_LIMIT = 10


@app.middleware("http")
async def login_rate_limit(request: Request, call_next):
    """Limit repeated login attempts per client IP without affecting normal API use."""
    if request.scope["path"].rstrip("/") == "/auth/login" and request.method.upper() == "POST":
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        attempts = _login_attempts[client_ip]
        while attempts and now - attempts[0] > _LOGIN_WINDOW_SECONDS:
            attempts.popleft()
        if len(attempts) >= _LOGIN_LIMIT:
            return JSONResponse(status_code=429, content={"detail": "Too many login attempts. Please wait one minute."})
        attempts.append(now)
    return await call_next(request)


@app.middleware("http")
async def api_prefix_compatibility(request: Request, call_next):
    """Expose the same routes under /api without breaking the existing portal client."""
    if request.scope["path"].startswith("/api/"):
        request.scope["path"] = request.scope["path"][4:]
    return await call_next(request)


Base.metadata.create_all(bind=engine)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(directory.router)
app.include_router(catalog.router)
app.include_router(tickets.router)
app.include_router(interventions.router)
app.include_router(ai.router)


@app.on_event("startup")
def startup() -> None:
    with SessionLocal() as db:
        run_startup_tasks(db, classifier)
