"""POST /api/chat — pergunta sobre a página. Resposta em STREAMING (SSE).

A resposta chega em pedaços (`data: <texto>\\n\\n`), para aparecer a fluir no
popup. No fim envia um evento `done`. Se não houver chave Claude, responde 200
com um evento `error` (a extensão mostra o modo básico) — não rebenta.
"""
from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.api.models.schemas import ChatRequest
from backend.api.services import chat_service
from backend.api.services.chat_service import MissingAnthropicKey

router = APIRouter()


def _sse(event: str, data: str) -> str:
    """Formata um evento SSE (UTF-8 legível; o cliente faz JSON.parse na mesma)."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    async def event_stream():
        try:
            async for piece in chat_service.stream_answer(req):
                yield _sse("token", piece)
            yield _sse("done", "")
        except MissingAnthropicKey:
            yield _sse(
                "error",
                "Sem Anthropic API key — o chat está em modo básico. Adiciona a tua "
                "chave nas Definições da extensão (BYOK) ou em backend/.env.",
            )
        except Exception as exc:  # degradação graciosa: nunca deixar a stream rebentar
            yield _sse("error", f"Erro ao gerar resposta: {exc}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
