# O backend e o scraping explicados de forma simples

> O backend (FastAPI) é o cérebro logístico: recebe a página, vai buscar mais
> contexto do site, enriquece, indexa, e serve as respostas. Aqui focamos as
> rotas e o scraping.

---

## O problema

O content script só vê **a página atual**. Mas para entender a *empresa*, precisas
de mais: a página "About", o "Pricing", a "FAQ", os "Docs". E precisas de texto
**limpo** — sem menus, anúncios e rodapés a poluir.

---

## As rotas (o mapa da API)

| Rota | Faz o quê |
|---|---|
| `POST /api/analyze` | recebe a página → scrape extra + enriquece + indexa no RAG |
| `POST /api/chat` | recebe pergunta → recupera contexto + chama o Claude (streaming) |
| `GET/DELETE /api/cache/{domain}` | ver/limpar cache + índice de um domínio |
| `GET /api/health` | estado + que chaves/serviços estão ativos |

Tudo montado em `backend/api/main.py`; cada rota num ficheiro de `routes/`, e a
lógica real nos `services/`. Separar rota (HTTP) de serviço (lógica) mantém tudo
testável.

---

## O scraping: duas ferramentas, dois trabalhos

Extrair conteúdo de HTML é duas coisas diferentes:

| Ferramenta | Trabalho |
|---|---|
| **trafilatura** | o **texto principal** já limpo (tira menus/rodapés/ads) |
| **BeautifulSoup** | os **metadados**: `<title>`, meta description, Open Graph, JSON-LD, links |

E o *crawl*: a partir dos links do mesmo domínio, escolhe os mais promissores
(About/Pricing/FAQ/Docs) e descarrega-os — em **paralelo**, com timeout e um limite
modesto (`MAX_SCRAPE_PAGES=8`) para não abusar do site nem da tua máquina.

---

## As partes mais importantes do código

### Peça 1 — Texto limpo com fallback · `scraper/extract.py`

```python
def extract_text(html):
    text = trafilatura.extract(html, include_tables=True)   # 1ª escolha
    if text:
        return text.strip()
    # Fallback: se o trafilatura falhar, BeautifulSoup tira scripts/styles.
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.get_text(" ").split())
```

Robustez: se a melhor ferramenta falhar numa página estranha, ainda tiramos texto
utilizável. Nunca ficamos sem nada.

### Peça 2 — Escolher os links certos · `scraper/extract.py`

```python
KEY_LINK_HINTS = ("about", "pricing", "faq", "docs", "features", "product", ...)

def rank_key_links(links, limit):
    def score(url):
        return sum(1 for h in KEY_LINK_HINTS if h in url.lower())
    ranked = sorted(links, key=score, reverse=True)
    useful = [u for u in ranked if score(u) > 0]
    return (useful or ranked)[:limit]
```

Não seguimos *todos* os links (seria lento e ruidoso). Priorizamos os que parecem
construir a imagem da empresa. Heurística simples, eficaz.

### Peça 3 — Crawl assíncrono e tolerante · `scraper/crawl.py`

```python
async with httpx.AsyncClient(headers=_HEADERS) as client:
    htmls = await asyncio.gather(*[_fetch(client, u) for u in targets])
# _fetch devolve None em erro → páginas falhadas são simplesmente ignoradas
```

Descarrega várias páginas ao mesmo tempo (`asyncio.gather`). Se uma falhar,
devolve `None` e seguimos — degradação graciosa outra vez.

### Peça 4 — Orquestração · `services/analyze_service.py`

```python
if not req.force_refresh and (cached := cache_service.get(domain)):
    return cached                                  # 1. cache
pages = [(page.url, page.text)]                    # 2. página atual
pages += [(p.url, p.text) for p in await crawl_key_pages(page.url, page.links)]  # 3. extra
chunks = pipeline.ingest(domain, pages)            # 4. indexa no RAG
company = await enrich_company(domain)             # 5. enriquece (opcional)
```

O maestro. Junta cache + scraping + RAG + enriquecimento numa análise só, e
guarda o resultado para a próxima visita ser instantânea.

---

**Resumo numa frase:** o backend recebe a página, vai buscar as páginas-chave do
mesmo site (texto limpo com trafilatura, metadados com BeautifulSoup), enriquece
com dados de empresa se houver chaves, indexa tudo no RAG por domínio, e guarda em
cache — tudo tolerante a falhas.
