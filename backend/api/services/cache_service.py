"""Cache por domínio da análise (para não re-scrapear/re-enriquecer sempre).

Simples e local: um ficheiro JSON por domínio em data/cache/, com timestamp.
Respeita CACHE_TTL_HOURS. Revisitar um site dentro do TTL é instantâneo.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from backend.api.models.schemas import AnalyzeResponse
from backend.config.settings import ROOT_DIR, settings

_CACHE_DIR = ROOT_DIR / "data" / "cache"


def _path(domain: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", domain)
    return _CACHE_DIR / f"{safe}.json"


def get(domain: str) -> AnalyzeResponse | None:
    """Devolve a análise cacheada se existir e não tiver expirado."""
    path = _path(domain)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    age_hours = (time.time() - raw.get("_cached_at", 0)) / 3600
    if age_hours > settings.cache_ttl_hours:
        return None

    payload = raw.get("payload")
    if not payload:
        return None
    resp = AnalyzeResponse(**payload)
    resp.cached = True
    return resp


def put(domain: str, response: AnalyzeResponse) -> None:
    """Guarda a análise de um domínio com timestamp."""
    record = {"_cached_at": time.time(), "payload": response.model_dump()}
    _path(domain).write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def exists(domain: str) -> bool:
    return get(domain) is not None


def clear(domain: str) -> bool:
    """Apaga o ficheiro de cache de um domínio. True se existia."""
    path = _path(domain)
    if path.exists():
        path.unlink()
        return True
    return False
