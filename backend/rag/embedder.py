"""Transforma texto em vetores (embeddings) — a peça que dá "busca por significado".

Usa um modelo pequeno e local (`bge-small`, ~130 MB) FORÇADO A CPU. Isto é
deliberado: num Mac de 8 GB, correr embeddings na GPU (Metal) competiria por
memória. Em CPU é lento mas leve e previsível, e os textos aqui são curtos.

O modelo é carregado uma única vez (lru_cache) — carregá-lo é a parte cara.
"""
from __future__ import annotations

from functools import lru_cache

from backend.config.settings import settings


@lru_cache
def _model():
    # Import tardio: só carrega sentence-transformers quando realmente precisamos
    # de embeddings (o /health e o chat básico não pagam este custo).
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model, device=settings.embedding_device)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Vetoriza uma lista de textos. Devolve uma lista de vetores (listas de floats)."""
    if not texts:
        return []
    vectors = _model().encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    """Vetoriza uma única pergunta (mesmo modelo dos documentos)."""
    return embed_texts([text])[0]
