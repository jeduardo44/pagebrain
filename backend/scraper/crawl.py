"""Crawling leve: busca páginas extra do mesmo domínio (About/Pricing/FAQ/Docs).

Assíncrono (httpx) com timeouts e um pequeno limite de páginas, para não abusar
do site nem da tua máquina. Respeita `max_scrape_pages` das settings.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from backend.config.settings import settings
from backend.scraper.extract import extract_text, rank_key_links

_HEADERS = {"User-Agent": "PageBrain/0.4 (+https://github.com/jeduardo44/pagebrain)"}


@dataclass
class ScrapedPage:
    url: str
    text: str


async def _fetch(client: httpx.AsyncClient, url: str) -> str | None:
    """Descarrega uma página; devolve None em erro (degradação graciosa)."""
    try:
        resp = await client.get(url, timeout=settings.request_timeout, follow_redirects=True)
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            return resp.text
    except (httpx.HTTPError, httpx.InvalidURL):
        return None
    return None


async def crawl_key_pages(base_url: str, candidate_links: list[str]) -> list[ScrapedPage]:
    """Descarrega e extrai texto das páginas-chave do mesmo domínio.

    Recebe os links já vistos pelo content script; escolhe os mais promissores.
    """
    targets = rank_key_links(candidate_links, limit=settings.max_scrape_pages)
    if not targets:
        return []

    async with httpx.AsyncClient(headers=_HEADERS) as client:
        htmls = await asyncio.gather(*[_fetch(client, u) for u in targets])

    pages: list[ScrapedPage] = []
    for url, html in zip(targets, htmls, strict=False):
        if not html:
            continue
        text = extract_text(html)
        if text and len(text) > 100:  # ignora páginas quase vazias
            pages.append(ScrapedPage(url=url, text=text))
    return pages
