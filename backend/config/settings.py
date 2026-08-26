"""Configuração central do PageBrain.

Lê o ficheiro `.env` (ou variáveis de ambiente) de forma tipada, via
pydantic-settings. Uma única instância `settings` é importada por todo o
backend — evita ler o ambiente em vários sítios.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do repo (…/pagebrain), para resolver caminhos relativos como o Chroma.
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Todas as opções configuráveis, com defaults sensatos."""

    # ── Claude API ────────────────────────────────────────────────────
    # Placeholder por omissão: o projeto arranca sem chave (modo básico).
    anthropic_api_key: str = "sk-ant-REPLACE_ME"
    claude_model: str = "claude-opus-5"

    # ── Enriquecimento externo (opcional) ─────────────────────────────
    brave_search_api_key: str = ""
    clearbit_api_key: str = ""

    # ── RAG / embeddings ──────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    # cpu evita competir por memória de GPU (importante num Mac de 8 GB).
    embedding_device: str = "cpu"

    # ── Scraping / cache ──────────────────────────────────────────────
    cache_ttl_hours: int = 24
    max_scrape_pages: int = 8
    request_timeout: int = 15

    # ── Infra ─────────────────────────────────────────────────────────
    log_level: str = "INFO"
    allowed_origins: str = "*"  # CORS; vírgula-separado ou "*"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Helpers derivados ─────────────────────────────────────────────
    @property
    def has_anthropic_key(self) -> bool:
        """True se há uma chave Claude real (não o placeholder)."""
        key = self.anthropic_api_key.strip()
        return bool(key) and key != "sk-ant-REPLACE_ME"

    @property
    def chroma_path(self) -> Path:
        p = (ROOT_DIR / self.chroma_persist_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cors_origins(self) -> list[str]:
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Instância única (cacheada) das settings."""
    return Settings()


settings = get_settings()
