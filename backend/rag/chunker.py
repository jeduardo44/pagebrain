"""Corta texto em pedaços ("chunks") para o RAG.

Um documento inteiro é grande demais para procurar/enviar. Cortamos em bocados
de ~512 tokens com sobreposição, para não partir uma ideia ao meio e para que
cada pedaço seja pequeno e fácil de encontrar por significado.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import tiktoken

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


@dataclass
class Chunk:
    chunk_id: str  # ex.: "example.com::about::3"
    source: str  # URL ou identificador da página de origem
    text: str
    index: int


@lru_cache
def _encoder() -> tiktoken.Encoding:
    # cl100k_base é um tokenizer genérico bom o suficiente para contar chunks.
    return tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Parte um texto em janelas de `size` tokens com `overlap` de sobreposição."""
    text = (text or "").strip()
    if not text:
        return []

    enc = _encoder()
    tokens = enc.encode(text)
    if len(tokens) <= size:
        return [text]

    step = max(size - overlap, 1)
    chunks: list[str] = []
    for start in range(0, len(tokens), step):
        window = tokens[start : start + size]
        if not window:
            break
        chunks.append(enc.decode(window))
        if start + size >= len(tokens):
            break
    return chunks


def chunk_page(source: str, text: str, domain: str) -> list[Chunk]:
    """Corta o texto de uma página e devolve Chunks com ids estáveis."""
    # slug curto da fonte para o id (evita ids gigantes com a URL inteira)
    slug = source.replace("https://", "").replace("http://", "").strip("/")
    slug = slug.replace("/", "_")[:60] or "page"
    return [
        Chunk(chunk_id=f"{domain}::{slug}::{i}", source=source, text=piece, index=i)
        for i, piece in enumerate(chunk_text(text))
    ]
