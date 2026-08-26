"""GET/DELETE /api/cache/{domain} — verificar e limpar a cache de um domínio."""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.services import cache_service
from backend.rag import store

router = APIRouter()


@router.get("/cache/{domain}")
async def get_cache(domain: str) -> dict:
    cached = cache_service.get(domain)
    return {
        "domain": domain,
        "cached": cached is not None,
        "chunks_indexed": store.count(domain),
    }


@router.delete("/cache/{domain}")
async def delete_cache(domain: str) -> dict:
    removed_cache = cache_service.clear(domain)
    removed_index = store.clear(domain)
    return {"domain": domain, "cache_cleared": removed_cache, "index_cleared": removed_index}
