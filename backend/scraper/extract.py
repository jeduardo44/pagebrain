"""Extração de conteúdo a partir de HTML.

Duas ferramentas, dois trabalhos:
  - trafilatura: extrai o TEXTO principal já limpo (sem menus/rodapés/ads).
  - BeautifulSoup: apanha os METADADOS (title, meta, Open Graph, JSON-LD) e links.
"""
from __future__ import annotations

import json
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def domain_of(url: str) -> str:
    """Devolve o domínio (netloc sem www) de uma URL."""
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def extract_text(html: str) -> str:
    """Texto principal limpo. Cai para BeautifulSoup se o trafilatura falhar."""
    try:
        import trafilatura

        text = trafilatura.extract(html, include_comments=False, include_tables=True)
        if text:
            return text.strip()
    except Exception:
        pass
    # Fallback: texto visível básico.
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.get_text(" ").split())


def extract_meta(html: str) -> dict[str, str]:
    """Recolhe <title>, meta description, Open Graph e Twitter cards."""
    soup = BeautifulSoup(html, "html.parser")
    meta: dict[str, str] = {}

    if soup.title and soup.title.string:
        meta["title"] = soup.title.string.strip()

    for tag in soup.find_all("meta"):
        key = tag.get("name") or tag.get("property")
        content = tag.get("content")
        if key and content:
            # BS4 pode devolver str ou lista; normalizamos para str.
            meta[str(key).lower()] = str(content).strip()

    return meta


def extract_jsonld(html: str) -> list[dict]:
    """Structured data (schema.org) embebida em <script type=application/ld+json>."""
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            if isinstance(data, list):
                out.extend(d for d in data if isinstance(d, dict))
            elif isinstance(data, dict):
                out.append(data)
        except (json.JSONDecodeError, TypeError):
            continue
    return out


def extract_links(html: str, base_url: str) -> list[str]:
    """Links absolutos do MESMO domínio (candidatos a scraping extra)."""
    soup = BeautifulSoup(html, "html.parser")
    base_domain = domain_of(base_url)
    seen: set[str] = set()
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        absolute = urljoin(base_url, str(a["href"])).split("#")[0]
        if domain_of(absolute) == base_domain and absolute not in seen:
            seen.add(absolute)
            links.append(absolute)
    return links


# Palavras que sugerem páginas úteis para construir a imagem da empresa.
KEY_LINK_HINTS = ("about", "pricing", "faq", "docs", "features", "product", "support", "contact")


def rank_key_links(links: list[str], limit: int) -> list[str]:
    """Ordena links pondo à frente os que parecem About/Pricing/FAQ/Docs."""

    def score(url: str) -> int:
        low = url.lower()
        return sum(1 for h in KEY_LINK_HINTS if h in low)

    ranked = sorted(links, key=score, reverse=True)
    # Só interessam os que têm alguma pista; senão devolve os primeiros na mesma.
    useful = [u for u in ranked if score(u) > 0]
    return (useful or ranked)[:limit]


# ── Deteção de tipo de página (heurística simples) ────────────────────
def detect_page_type(url: str, meta: dict[str, str], text: str) -> str:
    low = f"{url} {meta.get('og:type', '')} {text[:500]}".lower()
    if any(k in url.lower() for k in ("/docs", "/documentation", "developer")):
        return "docs"
    if any(k in low for k in ("pricing", "preços", "/plans")):
        return "pricing"
    if any(k in url.lower() for k in ("/blog", "/news", "/article")):
        return "blog"
    if any(k in url.lower() for k in ("/support", "/help", "/faq")):
        return "support"
    if any(k in low for k in ("dashboard", "console", "app.")):
        return "dashboard"
    return "landing"
