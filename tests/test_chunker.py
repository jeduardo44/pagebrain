"""Testes do chunker do RAG."""
from backend.rag.chunker import CHUNK_SIZE, chunk_page, chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_is_single_chunk():
    chunks = chunk_text("Olá mundo, isto é curto.")
    assert len(chunks) == 1


def test_long_text_is_split_with_overlap():
    # ~2000 palavras → vários chunks de ~512 tokens
    text = "palavra " * 2000
    chunks = chunk_text(text)
    assert len(chunks) > 1


def test_chunk_page_produces_stable_ids():
    page_chunks = chunk_page("https://acme.com/about", "conteúdo " * 400, "acme.com")
    assert page_chunks
    assert page_chunks[0].chunk_id.startswith("acme.com::")
    assert all(c.source == "https://acme.com/about" for c in page_chunks)


def test_chunk_size_constant_is_reasonable():
    assert 128 <= CHUNK_SIZE <= 2048
