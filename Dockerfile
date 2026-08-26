# Backend do PageBrain. Os embeddings correm em CPU (leve; sem GPU no contentor).
FROM python:3.12-slim

WORKDIR /app

# Deps de sistema mínimas (trafilatura/lxml precisam de build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instala só as dependências primeiro (melhor cache de camadas)
COPY pyproject.toml README.md ./
COPY backend ./backend
RUN pip install --no-cache-dir -e .

# Modelo de embeddings é descarregado no primeiro uso (não no build).
ENV EMBEDDING_DEVICE=cpu \
    CHROMA_PERSIST_DIR=/data/chroma \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
