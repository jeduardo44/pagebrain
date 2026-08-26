"""Integração com a Claude API — o "cérebro" que responde às perguntas.

Fluxo por pergunta:
  1. Garante que a página está indexada (se veio texto novo e o domínio está vazio).
  2. Recupera os excertos mais relevantes do RAG (por domínio).
  3. Junta contexto (empresa + excertos) da cache/RAG e monta o prompt.
  4. Chama o Claude (SDK oficial `anthropic`), com STREAMING.

Sem `ANTHROPIC_API_KEY` real → levanta MissingAnthropicKey (a rota trata disto e
a extensão cai em "modo básico").

O cliente é criado tardiamente e cacheado — os testes fazem monkeypatch a
`_client` para NÃO gastar tokens.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from backend.api.models.schemas import ChatRequest, ChatResponse, Citation
from backend.api.services import cache_service
from backend.config.settings import settings
from backend.prompts.system import SYSTEM_PROMPT
from backend.prompts.templates import build_context_block, build_user_turn
from backend.rag import pipeline
from backend.scraper.extract import domain_of

# Respostas de chat curtas: barato e rápido. Sobe se precisares de respostas longas.
_MAX_TOKENS = 4096


class MissingAnthropicKey(RuntimeError):
    """Levantada quando não há chave Claude configurada."""


@lru_cache
def _client():
    """Cliente async do Claude (criado uma vez). Testes fazem patch a isto."""
    from anthropic import AsyncAnthropic

    return AsyncAnthropic(api_key=settings.anthropic_api_key)


def _prepare(req: ChatRequest) -> tuple[str, list[dict], list[Citation]]:
    """Prepara (system, messages, citations) para a chamada ao Claude."""
    domain = req.domain or (domain_of(req.page.url) if req.page else "")

    # 1. Se veio página nova e o domínio ainda não tem nada indexado, indexa já.
    if req.page and req.page.text.strip() and pipeline.retrieve(domain, req.message) == []:
        pipeline.ingest(domain, [(req.page.url, req.page.text)])

    # 2. Recupera contexto relevante.
    hits = pipeline.retrieve(domain, req.message, top_k=5)
    citations = [Citation(chunk_id=h.chunk_id, source=h.source, score=h.score) for h in hits]

    # 3. Enriquece com o que estiver em cache (empresa + tipo de página).
    cached = cache_service.get(domain)
    company = cached.company if cached else None
    page_type = cached.page_type if cached else "unknown"

    context = build_context_block(
        domain=domain,
        page_type=page_type,
        retrieved_chunks=[h.text for h in hits],
        company=company,
    )
    user_turn = build_user_turn(context, req.message)

    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": user_turn})
    return SYSTEM_PROMPT, messages, citations


async def stream_answer(req: ChatRequest) -> AsyncGenerator[str, None]:
    """Gera a resposta do Claude em pedaços de texto (para SSE)."""
    if not settings.has_anthropic_key:
        raise MissingAnthropicKey

    system, messages, _ = _prepare(req)
    async with _client().messages.stream(
        model=settings.claude_model,
        max_tokens=_MAX_TOKENS,
        thinking={"type": "adaptive"},
        output_config={"effort": "low"},  # chat leve: menos "pensamento", mais rápido/barato
        system=system,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def answer(req: ChatRequest) -> ChatResponse:
    """Versão não-streaming (usada em testes e como fallback)."""
    if not settings.has_anthropic_key:
        raise MissingAnthropicKey

    system, messages, citations = _prepare(req)
    resp = await _client().messages.create(
        model=settings.claude_model,
        max_tokens=_MAX_TOKENS,
        thinking={"type": "adaptive"},
        output_config={"effort": "low"},
        system=system,
        messages=messages,
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return ChatResponse(
        answer=text,
        citations=citations,
        model=settings.claude_model,
        degraded=False,
    )
