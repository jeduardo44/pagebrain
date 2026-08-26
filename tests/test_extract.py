"""Testes do scraper (parsing de HTML)."""
from backend.scraper.extract import (
    detect_page_type,
    domain_of,
    extract_jsonld,
    extract_links,
    extract_meta,
    rank_key_links,
)

HTML = """
<html>
  <head>
    <title>Acme — Pagamentos</title>
    <meta name="description" content="A melhor API de pagamentos." />
    <meta property="og:site_name" content="Acme" />
    <script type="application/ld+json">
      {"@type": "Organization", "name": "Acme"}
    </script>
  </head>
  <body>
    <a href="/about">Sobre</a>
    <a href="https://acme.com/pricing">Preços</a>
    <a href="https://outrosite.com/x">Externo</a>
  </body>
</html>
"""


def test_domain_of_strips_www():
    assert domain_of("https://www.acme.com/x") == "acme.com"
    assert domain_of("https://acme.com") == "acme.com"


def test_extract_meta():
    meta = extract_meta(HTML)
    assert meta["title"] == "Acme — Pagamentos"
    assert meta["description"] == "A melhor API de pagamentos."
    assert meta["og:site_name"] == "Acme"


def test_extract_jsonld():
    data = extract_jsonld(HTML)
    assert data and data[0]["name"] == "Acme"


def test_extract_links_same_domain_only():
    links = extract_links(HTML, "https://acme.com/")
    assert "https://acme.com/about" in links
    assert "https://acme.com/pricing" in links
    assert all("outrosite.com" not in link for link in links)


def test_rank_key_links_prioritizes_hints():
    links = ["https://acme.com/random", "https://acme.com/pricing", "https://acme.com/about"]
    ranked = rank_key_links(links, limit=2)
    assert ranked[0] in ("https://acme.com/pricing", "https://acme.com/about")


def test_detect_page_type():
    assert detect_page_type("https://acme.com/docs/intro", {}, "") == "docs"
    assert detect_page_type("https://acme.com/pricing", {}, "planos e preços") == "pricing"
    assert detect_page_type("https://acme.com/", {}, "bem-vindo") == "landing"
