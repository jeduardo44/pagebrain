"""Testes da lógica BYOK (bring your own key) no chat_service.

Testam só a resolução de chave/modelo/parâmetros — não chamam o Claude.
"""
from backend.api.models.schemas import ChatRequest
from backend.api.services import chat_service


def _req(**kw) -> ChatRequest:
    return ChatRequest(domain="acme.com", message="oi", **kw)


def test_user_key_takes_priority(monkeypatch):
    monkeypatch.setattr(chat_service.settings, "anthropic_api_key", "sk-ant-SERVER")
    assert chat_service._resolve_key(_req(api_key="sk-ant-USER")) == "sk-ant-USER"


def test_falls_back_to_server_key(monkeypatch):
    monkeypatch.setattr(chat_service.settings, "anthropic_api_key", "sk-ant-SERVER")
    assert chat_service._resolve_key(_req()) == "sk-ant-SERVER"


def test_placeholder_is_not_a_valid_key(monkeypatch):
    monkeypatch.setattr(chat_service.settings, "anthropic_api_key", "sk-ant-REPLACE_ME")
    assert chat_service._resolve_key(_req()) is None
    # ...mas a chave do utilizador continua a valer
    assert chat_service._resolve_key(_req(api_key="sk-ant-USER")) == "sk-ant-USER"


def test_resolve_model_prefers_request(monkeypatch):
    monkeypatch.setattr(chat_service.settings, "claude_model", "claude-opus-5")
    assert chat_service._resolve_model(_req(model="claude-haiku-4-5")) == "claude-haiku-4-5"
    assert chat_service._resolve_model(_req()) == "claude-opus-5"


def test_thinking_params_only_for_supported_models():
    # opus/sonnet-5/fable → adaptive + effort
    assert "thinking" in chat_service._thinking_params("claude-opus-5")
    assert "thinking" in chat_service._thinking_params("claude-sonnet-5")
    # haiku (antigo) → sem thinking/effort (senão daria 400)
    assert chat_service._thinking_params("claude-haiku-4-5") == {}
