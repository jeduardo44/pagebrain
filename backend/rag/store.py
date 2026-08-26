"""Vector store local (ChromaDB), com UMA coleção por domínio.

Porquê por domínio? Isolamento e memória: cada site constrói a sua própria base
de conhecimento, e uma pergunta sobre `acme.com` nunca recupera excertos de
`outrosite.com`. Revisitar um site já indexado é instantâneo.

No README original isto seria pgvector no Cloud SQL. Aqui é Chroma persistente
local (grava num diretório), sem servidor nem Docker obrigatório.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import chromadb

from backend.config.settings import settings
from backend.rag.chunker import Chunk


@dataclass
class Hit:
    chunk_id: str
    source: str
    text: str
    score: float  # 0..1, maior = mais parecido


@lru_cache
def _client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=str(settings.chroma_path))


def _collection_name(domain: str) -> str:
    """Nome de coleção válido para o Chroma a partir de um domínio."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", domain).strip("_")
    # Chroma exige 3-63 chars; garantimos o mínimo.
    return f"dom_{safe}"[:63] if safe else "dom_default"


def _collection(domain: str):
    return _client().get_or_create_collection(
        name=_collection_name(domain),
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(domain: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
    """Guarda chunks + embeddings na coleção do domínio."""
    if not chunks:
        return
    _collection(domain).add(
        ids=[c.chunk_id for c in chunks],
        embeddings=vectors,
        documents=[c.text for c in chunks],
        metadatas=[{"source": c.source, "index": c.index} for c in chunks],
    )


def search(domain: str, query_vector: list[float], top_k: int = 5) -> list[Hit]:
    """Devolve os top_k chunks mais parecidos com a pergunta, dentro do domínio."""
    col = _collection(domain)
    if col.count() == 0:
        return []
    res = col.query(query_embeddings=[query_vector], n_results=min(top_k, col.count()))
    hits: list[Hit] = []
    for cid, text, meta, dist in zip(
        res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0], strict=False
    ):
        # Chroma devolve DISTÂNCIA (0 = idêntico). Convertemos para score (maior = melhor).
        hits.append(
            Hit(
                chunk_id=cid,
                source=str(meta.get("source", "")),
                text=text,
                score=1.0 - float(dist),
            )
        )
    return hits


def count(domain: str) -> int:
    return _collection(domain).count()


def clear(domain: str) -> bool:
    """Apaga a coleção de um domínio. True se existia."""
    try:
        _client().delete_collection(_collection_name(domain))
        return True
    except Exception:
        return False
