"""Testes das rotas HTTP com o TestClient do FastAPI.

O chat é mockado — NÃO chama o Claude, não gasta tokens, não precisa de chave.
"""
from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.services import chat_service
from backend.api.services.chat_service import MissingAnthropicKey

client = TestClient(app)


def test_health_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "anthropic_key" in body
    assert "model" in body


def test_root():
    assert client.get("/").status_code == 200


def test_chat_streams_tokens(monkeypatch):
    async def fake_stream(req) -> AsyncGenerator[str, None]:
        for piece in ["Olá", ", ", "mundo!"]:
            yield piece

    monkeypatch.setattr(chat_service, "stream_answer", fake_stream)

    resp = client.post("/api/chat", json={"domain": "acme.com", "message": "oi"})
    assert resp.status_code == 200
    text = resp.text
    assert "event: token" in text
    assert "event: done" in text
    assert "mundo!" in text


def test_chat_without_key_emits_error(monkeypatch):
    async def raising_stream(req) -> AsyncGenerator[str, None]:
        raise MissingAnthropicKey
        yield  # pragma: no cover  (torna a função um gerador)

    monkeypatch.setattr(chat_service, "stream_answer", raising_stream)

    resp = client.post("/api/chat", json={"domain": "acme.com", "message": "oi"})
    assert resp.status_code == 200
    assert "event: error" in resp.text
    assert "modo básico" in resp.text


def test_cache_endpoints():
    # GET num domínio inexistente
    resp = client.get("/api/cache/inexistente.example")
    assert resp.status_code == 200
    assert resp.json()["cached"] is False

    # DELETE devolve estado
    resp = client.delete("/api/cache/inexistente.example")
    assert resp.status_code == 200
    assert "cache_cleared" in resp.json()
