"""Enriquecimento via Brave Search (notícias/reviews recentes sobre a empresa).

Implementado a sério, mas INERTE sem `BRAVE_SEARCH_API_KEY`. Obter chave em:
https://brave.com/search/api/
"""
from __future__ import annotations

import httpx

from backend.api.models.schemas import CompanyInfo
from backend.config.settings import settings
from backend.enrichment.base import Enricher

_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


class BraveEnricher(Enricher):
    name = "brave"

    @property
    def enabled(self) -> bool:
        return bool(settings.brave_search_api_key.strip())

    async def enrich(self, domain: str) -> CompanyInfo:
        if not self.enabled:
            return CompanyInfo()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    _ENDPOINT,
                    params={"q": f"{domain} company news", "count": 5},
                    headers={
                        "Accept": "application/json",
                        "X-Subscription-Token": settings.brave_search_api_key,
                    },
                    timeout=settings.request_timeout,
                )
            if resp.status_code != 200:
                return CompanyInfo()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            return CompanyInfo()

        results = (data.get("web") or {}).get("results") or []
        news = [r.get("title", "") for r in results[:5] if r.get("title")]
        return CompanyInfo(domain=domain, news=news, sources=[self.name] if news else [])
