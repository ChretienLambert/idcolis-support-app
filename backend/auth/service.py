from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Iterable

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import RefreshSession, Role, User, UserAgency, utcnow
from ..schemas import AuthSessionSchema, AuthUserSchema


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _build_user_schema(self, user: User) -> AuthUserSchema:
        assignment = self.db.execute(select(UserAgency).where(UserAgency.user_id == user.id)).scalar_one_or_none()
        return AuthUserSchema(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.name,
            is_active=user.is_active,
            region=user.region,
            department=user.department,
            agency=assignment.agency if assignment else None,
        )

    def _issue_session(self, user: User, agency: str | None = None, station: str | None = None) -> AuthSessionSchema:
        now = utcnow()
        access_expires_at = now + timedelta(minutes=settings.access_token_minutes)
        session_id = secrets.token_urlsafe(24)
        session_key = secrets.token_urlsafe(32)
        access_jti = secrets.token_urlsafe(24)

        access_payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role.name,
            "sid": session_id,
            "token_type": "access",
            "iat": int(now.timestamp()),
            "exp": int(access_expires_at.timestamp()),
            "jti": access_jti,
            "agency": agency,
            "station": station,
        }
        access_token = _encode(access_payload)

        session_row = RefreshSession(
            session_id=session_id,
            session_key_hash=_hash_secret(session_key),
            access_token_jti=access_jti,
            user_id=user.id,
            expires_at=access_expires_at,
            created_at=now,
        )
        self.db.add(session_row)
        self.db.commit()
        self.db.refresh(session_row)
        return AuthSessionSchema(
            user=self._build_user_schema(user),
            access_token=access_token,
            refresh_token="",
            session_id=session_id,
            session_key=session_key,
            access_expires_at=access_expires_at,
            refresh_expires_at=access_expires_at,
        )

    def sign_in(self, email: str | None, password: str, agency: str | None = None, station: str | None = None, name: str | None = None) -> AuthSessionSchema:
        if email:
            stmt = select(User).join(Role).where(User.email == email.lower().strip())
        elif name:
            stmt = select(User).join(Role).where(User.full_name == name.strip())
        else:
            raise ValueError("Name or email is required.")
        user = self.db.execute(stmt).scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials.")
        if not user.is_active:
            raise ValueError("Account disabled.")
        if user.role.name in {"Utilisateur", "Régulateur_Agence", "Support_IT"}:
            assignment = self.db.execute(select(UserAgency).where(UserAgency.user_id == user.id)).scalar_one_or_none()
            if user.role.name == "Utilisateur":
                if not assignment or assignment.agency != agency or (station and assignment.station != station):
                    raise ValueError("This account is not assigned to the selected agency.")
            elif user.role.name == "Régulateur_Agence":
                if not assignment or assignment.agency != agency:
                    raise ValueError("This regulator is not assigned to the selected agency.")
            elif assignment and agency and assignment.agency != agency:
                raise ValueError("This account is not assigned to the selected agency.")
        return self._issue_session(user, agency, station)


    def restore(self, session_id: str, session_key: str, agency: str | None = None, station: str | None = None) -> AuthSessionSchema:
        session = self.db.execute(select(RefreshSession).where(RefreshSession.session_id == session_id)).scalar_one_or_none()
        if not session or not session.is_active() or _hash_secret(session_key) != session.session_key_hash:
            raise ValueError("Session expired or revoked.")
        user = self.db.get(User, session.user_id)
        if not user:
            raise ValueError("User not found.")
        return self._issue_session(user, agency, station)

    def revoke(self, session_id: str | None = None, session_key: str | None = None) -> None:
        session: RefreshSession | None = None
        if session_id:
            session = self.db.execute(select(RefreshSession).where(RefreshSession.session_id == session_id)).scalar_one_or_none()
        if session and session_key and _hash_secret(session_key) != session.session_key_hash:
            return
        if session:
            session.revoked_at = utcnow()
            self.db.commit()

    def current_user(self, access_token: str) -> User:
        payload = _decode(access_token)
        if payload.get("token_type") != "access":
            raise ValueError("Invalid access token.")
        session_id = payload.get("sid")
        access_jti = payload.get("jti")
        session = self.db.execute(select(RefreshSession).where(RefreshSession.session_id == session_id)).scalar_one_or_none()
        if not session or not session.is_active() or session.access_token_jti != access_jti:
            raise ValueError("Session expired or revoked.")
        user = self.db.get(User, payload["sub"])
        if not user:
            raise ValueError("User not found.")
        # The tenant is attached to the request user for downstream authorization.
        token_agency = payload.get("agency")
        if user.role.name == "Régulateur_Agence":
            assignment = self.db.execute(select(UserAgency).where(UserAgency.user_id == user.id)).scalar_one_or_none()
            user._agency_scope = assignment.agency if assignment else token_agency
        else:
            user._agency_scope = token_agency
        return user

    def token_agency(self, access_token: str) -> str | None:
        return _decode(access_token).get("agency")

    def require_role(self, user: User, allowed_roles: Iterable[str]) -> None:
        if user.role.name not in set(allowed_roles):
            raise PermissionError("Forbidden.")

    def verify_access_claims(self, access_token: str) -> dict:
        return _decode(access_token)



