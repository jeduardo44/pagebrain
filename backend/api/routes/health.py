"""GET /api/health — estado do backend e que serviços/chaves estão ativos.

A extensão usa isto para saber se pode ativar o chat ou se deve mostrar o
"modo básico".
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.models.schemas import HealthResponse
from backend.config.settings import settings
from backend.enrichment.aggregate import active_enrichers

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    active = active_enrichers()
    return HealthResponse(
        status="ok",
        anthropic_key=settings.has_anthropic_key,
        brave_enabled="brave" in active,
        clearbit_enabled="clearbit" in active,
        model=settings.claude_model,
    )
