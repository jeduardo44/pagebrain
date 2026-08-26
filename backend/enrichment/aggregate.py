"""Junta todos os enriquecedores numa só chamada e funde os resultados.

Corre os enriquecedores ATIVOS em paralelo e combina os campos preenchidos.
Se nenhum estiver ativo (sem chaves), devolve CompanyInfo vazio — sem erro.
"""
from __future__ import annotations

import asyncio

from backend.api.models.schemas import CompanyInfo
from backend.enrichment.base import Enricher
from backend.enrichment.brave import BraveEnricher
from backend.enrichment.clearbit import ClearbitEnricher

_ENRICHERS: list[Enricher] = [ClearbitEnricher(), BraveEnricher()]


def active_enrichers() -> list[str]:
    return [e.name for e in _ENRICHERS if e.enabled]


def _merge(base: CompanyInfo, other: CompanyInfo) -> CompanyInfo:
    """Preenche campos vazios de `base` com os de `other`; junta as listas."""
    for field in ("name", "domain", "description", "industry", "employees", "funding"):
        if not getattr(base, field) and getattr(other, field):
            setattr(base, field, getattr(other, field))
    base.competitors = list(dict.fromkeys(base.competitors + other.competitors))
    base.tech_stack = list(dict.fromkeys(base.tech_stack + other.tech_stack))
    base.news = list(dict.fromkeys(base.news + other.news))
    base.sources = list(dict.fromkeys(base.sources + other.sources))
    return base


async def enrich_company(domain: str) -> CompanyInfo:
    """Corre os enriquecedores ativos em paralelo e funde tudo."""
    active = [e for e in _ENRICHERS if e.enabled]
    if not active:
        return CompanyInfo(domain=domain)

    results = await asyncio.gather(*[e.enrich(domain) for e in active], return_exceptions=True)

    merged = CompanyInfo(domain=domain)
    for r in results:
        if isinstance(r, CompanyInfo):
            merged = _merge(merged, r)
    return merged
