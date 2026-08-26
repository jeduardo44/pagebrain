"""Enriquecimento via Clearbit (dados de empresa: indústria, tamanho, etc.).

Implementado a sério, mas INERTE sem `CLEARBIT_API_KEY`. Obter chave em:
https://clearbit.com/ (Enrichment API).
"""
from __future__ import annotations

import httpx

from backend.api.models.schemas import CompanyInfo
from backend.config.settings import settings
from backend.enrichment.base import Enricher

_ENDPOINT = "https://company.clearbit.com/v2/companies/find"


class ClearbitEnricher(Enricher):
    name = "clearbit"

    @property
    def enabled(self) -> bool:
        return bool(settings.clearbit_api_key.strip())

    async def enrich(self, domain: str) -> CompanyInfo:
        if not self.enabled:
            return CompanyInfo()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    _ENDPOINT,
                    params={"domain": domain},
                    headers={"Authorization": f"Bearer {settings.clearbit_api_key}"},
                    timeout=settings.request_timeout,
                )
            if resp.status_code != 200:
                return CompanyInfo()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            return CompanyInfo()

        metrics = data.get("metrics") or {}
        category = data.get("category") or {}
        tech = data.get("tech") or []
        return CompanyInfo(
            name=data.get("name", ""),
            domain=domain,
            description=data.get("description", ""),
            industry=category.get("industry", ""),
            employees=str(metrics.get("employees", "") or ""),
            tech_stack=list(tech)[:10],
            sources=[self.name],
        )
