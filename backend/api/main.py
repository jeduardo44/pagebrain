"""Aplicação FastAPI do PageBrain — monta as rotas e o CORS.

Corre com:  make run   (ou: uvicorn backend.api.main:app --reload)
Docs interativas em:  http://localhost:8000/docs
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import analyze, cache, chat, health
from backend.config.settings import settings

logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="PageBrain",
    description="Backend que entende a página onde estás e responde com o Claude.",
    version="0.4.0",
)

# A extensão chama o backend a partir de chrome-extension://... — o CORS
# precisa de permitir essas origens (por omissão "*" em dev).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Todas as rotas sob /api
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(cache.router, prefix="/api", tags=["cache"])


@app.get("/")
async def root() -> dict:
    return {"name": "PageBrain", "docs": "/docs", "health": "/api/health"}
