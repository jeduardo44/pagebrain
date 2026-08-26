"""Pipeline RAG: juntar chunker + embedder + store num fluxo simples.

- ingest(): pega no texto de uma ou mais páginas → corta → vetoriza → guarda.
- retrieve(): pega numa pergunta → vetoriza → devolve os excertos mais relevantes.
"""
from __future__ import annotations

from backend.rag import store
from backend.rag.chunker import chunk_page
from backend.rag.embedder import embed_query, embed_texts
from backend.rag.store import Hit


def ingest(domain: str, pages: list[tuple[str, str]]) -> int:
    """Indexa páginas (lista de (source_url, text)). Devolve nº de chunks indexados."""
    all_chunks = []
    for source, text in pages:
        all_chunks.extend(chunk_page(source, text, domain))

    if not all_chunks:
        return 0

    vectors = embed_texts([c.text for c in all_chunks])
    store.add_chunks(domain, all_chunks, vectors)
    return len(all_chunks)


def retrieve(domain: str, question: str, top_k: int = 5) -> list[Hit]:
    """Devolve os top_k excertos mais relevantes para a pergunta, no domínio."""
    if store.count(domain) == 0:
        return []
    return store.search(domain, embed_query(question), top_k=top_k)
