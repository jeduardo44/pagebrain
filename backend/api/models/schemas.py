"""Schemas Pydantic v2 — os contratos entre a extensão e o backend.

Definir isto num sítio só dá validação automática (FastAPI rejeita pedidos
malformados) e documentação grátis em /docs.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


# ── Conteúdo extraído pela extensão (content script) ─────────────────
class ExtractedPage(BaseModel):
    """O que o content script consegue ver na página atual, no browser."""

    url: str
    title: str = ""
    text: str = ""  # texto principal já limpo pelo content script
    description: str = ""  # <meta name=description> ou og:description
    meta: dict[str, str] = Field(default_factory=dict)  # OG, twitter, etc.
    jsonld: list[dict] = Field(default_factory=list)  # structured data
    links: list[str] = Field(default_factory=list)  # links do mesmo domínio


# ── /api/analyze ─────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    page: ExtractedPage
    force_refresh: bool = False  # ignora cache e re-analisa


class CompanyInfo(BaseModel):
    """Dados de empresa (enriquecimento). Tudo opcional — degradação graciosa."""

    name: str = ""
    domain: str = ""
    description: str = ""
    industry: str = ""
    employees: str = ""
    funding: str = ""
    competitors: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    news: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)  # que APIs contribuíram


class AnalyzeResponse(BaseModel):
    domain: str
    page_type: str = "unknown"  # landing, docs, pricing, blog, support, dashboard
    summary: str = ""
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    pages_scraped: int = 0
    chunks_indexed: int = 0
    cached: bool = False
    degraded: bool = False  # True se faltou alguma peça (ex.: sem chaves)


# ── /api/chat ────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    domain: str
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    # Contexto da página atual, caso ainda não tenha sido analisada/indexada.
    page: ExtractedPage | None = None
    # BYOK ("bring your own key"): a extensão pode enviar a chave e o modelo do
    # próprio utilizador. Se vierem, têm prioridade sobre o .env do servidor.
    api_key: str | None = None
    model: str | None = None


class Citation(BaseModel):
    chunk_id: str
    source: str
    score: float


class ChatResponse(BaseModel):
    """Usado quando NÃO se faz streaming (ex.: modo não-stream / testes)."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    model: str = ""
    degraded: bool = False


# ── /api/health ──────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str = "ok"
    anthropic_key: bool = False
    brave_enabled: bool = False
    clearbit_enabled: bool = False
    model: str = ""
