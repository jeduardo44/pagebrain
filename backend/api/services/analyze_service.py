"""Orquestra a análise de uma página: scraping extra + enriquecimento + RAG.

Fluxo:
  1. Se houver cache válido para o domínio → devolve logo (a não ser force_refresh).
  2. Indexa o conteúdo da página atual no RAG (por domínio).
  3. Descarrega páginas-chave do mesmo site e indexa-as também.
  4. Enriquece com dados de empresa (se houver chaves).
  5. Deteta o tipo de página, guarda em cache e devolve.
"""
from __future__ import annotations

from backend.api.models.schemas import AnalyzeRequest, AnalyzeResponse
from backend.api.services import cache_service
from backend.enrichment.aggregate import active_enrichers, enrich_company
from backend.rag import pipeline
from backend.scraper.crawl import crawl_key_pages
from backend.scraper.extract import detect_page_type, domain_of


async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    page = req.page
    domain = domain_of(page.url)

    # 1. Cache
    if not req.force_refresh:
        cached = cache_service.get(domain)
        if cached:
            return cached

    degraded = False

    # 2. Indexa a página atual (o content script já nos deu o texto).
    pages_to_index: list[tuple[str, str]] = []
    if page.text.strip():
        pages_to_index.append((page.url, page.text))

    # 3. Scraping extra das páginas-chave do mesmo domínio.
    scraped = await crawl_key_pages(page.url, page.links)
    pages_to_index.extend((p.url, p.text) for p in scraped)

    chunks_indexed = pipeline.ingest(domain, pages_to_index)

    # 4. Enriquecimento (só se houver chaves; senão fica vazio).
    company = await enrich_company(domain)
    company.name = company.name or page.meta.get("og:site_name", "") or domain
    company.description = company.description or page.description
    if not active_enrichers():
        degraded = True  # sem enriquecimento externo

    # 5. Tipo de página + resumo curto (o texto inicial serve de sumário base).
    page_type = detect_page_type(page.url, page.meta, page.text)
    summary = (page.description or page.text[:280]).strip()

    resp = AnalyzeResponse(
        domain=domain,
        page_type=page_type,
        summary=summary,
        company=company,
        pages_scraped=len(scraped),
        chunks_indexed=chunks_indexed,
        cached=False,
        degraded=degraded,
    )
    cache_service.put(domain, resp)
    return resp
