from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth.deps import get_auth_service, get_current_user
from ..logging import build_logger
from ..schemas import AuthSessionSchema, AuthUserSchema, LoginRequest, LogoutRequest, RestoreSessionRequest
from ..serializers import user_schema

router = APIRouter(prefix="/auth")
auth_logger = build_logger("ID Colis.auth", "auth.log")


@router.post("/login", response_model=AuthSessionSchema)
def login(payload: LoginRequest, service=Depends(get_auth_service)):
    try:
        session = service.sign_in(payload.email, payload.password, payload.agency, payload.station, payload.name)
        auth_logger.info("login_attempt email=%s result=success role=%s", payload.email, session.user.role)
        return session
    except Exception as exc:
        auth_logger.info("login_attempt email=%s result=failure reason=%s", payload.email, type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.") from exc


@router.post("/restore", response_model=AuthSessionSchema)
def restore(payload: RestoreSessionRequest, service=Depends(get_auth_service)):
    try:
        return service.restore(payload.session_id, payload.session_key, payload.agency)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout")
def logout(payload: LogoutRequest, service=Depends(get_auth_service)):
    service.revoke(payload.session_id, payload.session_key)
    return {"ok": True}


@router.get("/me", response_model=AuthUserSchema)
def me(user=Depends(get_current_user)):
    return user_schema(user)
