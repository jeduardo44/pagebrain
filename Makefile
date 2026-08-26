# Atalhos do PageBrain. Corre `make ajuda`.
.PHONY: ajuda setup run test lint type fmt docker clean

PY=.venv/bin/python
PIP=.venv/bin/pip

ajuda:
	@echo "Passos:"
	@echo "  make setup   -> cria venv (python3.12) e instala deps (backend + dev)"
	@echo "  make run     -> sobe o backend em http://localhost:8000 (docs em /docs)"
	@echo "  make test    -> corre os testes (não gastam tokens; Claude é mockado)"
	@echo "  make lint    -> ruff (estilo/erros)"
	@echo "  make type    -> mypy (tipos)"
	@echo "  make fmt     -> ruff --fix (arruma imports/estilo)"
	@echo "  make docker  -> sobe o backend via docker-compose"
	@echo ""
	@echo "Extensão: chrome://extensions -> Developer mode -> Load unpacked -> pasta extension/"

setup:
	python3.12 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "OK. Ativa com: source .venv/bin/activate   e copia .env.example -> .env"

run:
	.venv/bin/uvicorn backend.api.main:app --reload --port 8000

test:
	$(PY) -m pytest -q

lint:
	.venv/bin/ruff check backend tests

type:
	.venv/bin/mypy backend

fmt:
	.venv/bin/ruff check --fix backend tests

docker:
	docker-compose up --build

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
