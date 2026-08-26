"""Testes do cache por domínio (put/get/TTL/clear)."""
from backend.api.models.schemas import AnalyzeResponse
from backend.api.services import cache_service


def _sample(domain: str) -> AnalyzeResponse:
    return AnalyzeResponse(domain=domain, page_type="landing", summary="teste")


def test_put_and_get_roundtrip():
    domain = "test-roundtrip.example"
    cache_service.clear(domain)
    cache_service.put(domain, _sample(domain))
    got = cache_service.get(domain)
    assert got is not None
    assert got.domain == domain
    assert got.cached is True  # marcado como vindo da cache
    cache_service.clear(domain)


def test_get_missing_returns_none():
    assert cache_service.get("nao-existe.example") is None


def test_ttl_expiry(monkeypatch):
    domain = "test-ttl.example"
    cache_service.put(domain, _sample(domain))
    # Força TTL = 0 → tudo expira imediatamente.
    monkeypatch.setattr(cache_service.settings, "cache_ttl_hours", 0)
    assert cache_service.get(domain) is None
    cache_service.clear(domain)


def test_clear_returns_true_when_existed():
    domain = "test-clear.example"
    cache_service.put(domain, _sample(domain))
    assert cache_service.clear(domain) is True
    assert cache_service.clear(domain) is False
