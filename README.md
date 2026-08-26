# 🧠 PageBrain

> An AI-powered Chrome Extension that actually understands the page you're on — the company behind it, how the product works, and how to help you use it. No more dumb chatbots.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-green.svg)](https://python.org)
[![Chrome Extension](https://img.shields.io/badge/Chrome-Manifest%20V3-orange.svg)](https://developer.chrome.com/docs/extensions/mv3/)

---

## The Problem

Every website has a chatbot. Almost all of them are useless — they loop you through FAQ trees, can't answer anything specific, and have no real understanding of the product or company behind the page.

**PageBrain** replaces that experience. Click the extension icon on any page and get an assistant that:

- Knows what the page is about (scraped and parsed in real time)
- Knows who the company is (funding, team, product, competitors)
- Can help you operate the product (docs, FAQs, how-tos — all ingested)
- Remembers context across pages on the same site

---

## How It Works

```
┌──────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│ Chrome Extension │────▶│  FastAPI Backend  │────▶│   Claude API    │
│  (Manifest V3)   │◀────│                   │◀────│   (Anthropic)   │
│                  │     │  ┌─────────────┐  │     └─────────────────┘
│ • content script │     │  │  Scraper    │  │
│ • popup UI       │     │  │  Enrichment │  │     ┌─────────────────┐
│ • service worker │     │  │  RAG + Cache│  │────▶│  External APIs  │
└──────────────────┘     └──┴─────────────┴──┘     │ (Clearbit,Brave)│
                                                    └─────────────────┘
```

1. **You visit a page** → the content script extracts text, metadata, structured data, and key links
2. **You open the popup** → the backend scrapes additional pages from the same site (About, Pricing, FAQ, Docs)
3. **Enrichment layer** → optional external APIs add company data (funding, team size, tech stack)
4. **RAG pipeline** → all content is chunked, embedded, and stored **per domain** in ChromaDB
5. **You ask a question** → relevant context is retrieved and sent to Claude with your question
6. **Claude answers** → streaming, with deep, specific knowledge about that exact page and company

> **Learning-first:** this repo is also a study project. See the plain-language guides in [`docs/`](docs/) — start with [`docs/00_visao_geral.md`](docs/00_visao_geral.md).

---

## Project Structure

```
pagebrain/
├── extension/            # Chrome MV3 (vanilla JS): manifest, popup, background, content, options, assets
├── backend/
│   ├── api/              # FastAPI app, routes, services, Pydantic schemas
│   ├── scraper/          # extract (trafilatura + BS4) + crawl (same-domain pages)
│   ├── enrichment/       # Clearbit + Brave (optional, graceful without keys)
│   ├── rag/              # chunker + embedder (bge-small, CPU) + Chroma store (per domain)
│   ├── prompts/          # system prompt + context templates
│   └── config/           # settings (pydantic-settings, reads .env)
├── tests/                # pytest (Claude is mocked — no tokens spent)
├── docs/                 # didactic guides, one per component
├── Dockerfile · docker-compose.yml · Makefile · pyproject.toml
└── .github/workflows/    # CI: ruff + mypy + pytest
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Claude API (Anthropic) via the official `anthropic` SDK — default `claude-opus-5` |
| Backend | Python 3.12, FastAPI, uvicorn |
| Scraping | BeautifulSoup4, trafilatura, httpx (async) |
| Embeddings | sentence-transformers `bge-small` (local, **CPU** — light on an 8 GB Mac) |
| Vector Store | ChromaDB (local, persistent, one collection per domain) |
| Validation | Pydantic v2 + pydantic-settings |
| Extension | Chrome Manifest V3, vanilla JS |
| Tooling | ruff, mypy, pytest |
| Infra | Docker, docker-compose, GitHub Actions |

---

## Getting Started

### Prerequisites
- Python 3.12+
- Google Chrome
- An [Anthropic API key](https://console.anthropic.com/) (for the chat to answer — everything else runs without it)

### Backend

```bash
git clone https://github.com/jeduardo44/pagebrain.git
cd pagebrain

make setup                 # creates .venv (python3.12) and installs deps
source .venv/bin/activate
cp .env.example .env        # then edit .env and add your ANTHROPIC_API_KEY
make run                    # http://localhost:8000  (docs at /docs)
```

### Extension

1. Open `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** and select the `extension/` folder
4. Open any page and click the PageBrain icon

### Docker (alternative)

```bash
cp .env.example .env        # add your key
docker-compose up --build
```

---

## Getting an Anthropic API key

1. Create an account at <https://console.anthropic.com/>
2. **Settings → API Keys → Create Key**, copy the `sk-ant-...` value
3. Put it in `.env` as `ANTHROPIC_API_KEY=sk-ant-...` (the `.env` is gitignored)

**Cost note:** the default model is `claude-opus-5` ($5 / $25 per 1M tokens — powerful but pricey). For a page chatbot, `claude-sonnet-5` ($2/$10) or `claude-haiku-4-5` ($1/$5) are much cheaper — switch via `CLAUDE_MODEL` in `.env`.

The **Brave** and **Clearbit** keys are optional: without them the external enrichment is simply skipped and everything else works.

---

## Configuration (`.env`)

| Key | Required | Default | What it does |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | for chat | placeholder | your Claude key |
| `CLAUDE_MODEL` | no | `claude-opus-5` | which model answers |
| `BRAVE_SEARCH_API_KEY` | no | — | company news enrichment |
| `CLEARBIT_API_KEY` | no | — | company data enrichment |
| `EMBEDDING_DEVICE` | no | `cpu` | keep `cpu` on low-RAM machines |
| `MAX_SCRAPE_PAGES` | no | `8` | how many extra pages to crawl |
| `CACHE_TTL_HOURS` | no | `24` | domain cache lifetime |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze` | Receives extracted page, scrapes + enriches + indexes, returns analysis |
| `POST` | `/api/chat` | Receives message + context, streams Claude's response (SSE) |
| `GET` | `/api/cache/{domain}` | Check cached data / index size for a domain |
| `DELETE` | `/api/cache/{domain}` | Clear cache + vector index for a domain |
| `GET` | `/api/health` | Health check + which keys/services are active |

Interactive docs: <http://localhost:8000/docs>

---

## Development

```bash
make fmt    # ruff --fix
make lint   # ruff check
make type   # mypy
make test   # pytest — no tokens spent, Claude is mocked
```

Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Roadmap

- **v0.1 MVP** — extension + FastAPI + Claude chat on any page ✅
- **v0.2 Enrichment** — same-site scraping, per-domain cache, quick actions, persistent history ✅
- **v0.3 RAG + External** — ChromaDB pipeline, Clearbit/Brave, page-type detection, source indicators ✅
- **v0.4 Polish** — graceful degradation, options page, tests, Docker/CI ✅ · Chrome Web Store listing (pending)

---

## License

MIT — see [LICENSE](LICENSE).
