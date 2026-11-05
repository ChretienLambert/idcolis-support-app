from __future__ import annotations

from fastapi import APIRouter

from ..config import settings
from ..schemas import HealthSchema

router = APIRouter()


@router.get("/health", response_model=HealthSchema)
def health():
    return HealthSchema(ok=True, env=settings.env)
