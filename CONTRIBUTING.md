# Contributing to PageBrain

Thanks for your interest! This is a learning project, kept simple and readable.

## Setup

```bash
make setup                 # venv (python3.12) + deps
source .venv/bin/activate
cp .env.example .env        # add your ANTHROPIC_API_KEY
pre-commit install
```

## Workflow

- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Before a PR:
  ```bash
  make fmt    # ruff --fix
  make lint   # ruff check
  make type   # mypy
  make test   # pytest (no tokens spent — Claude is mocked)
  ```
- Keep functions small and commented with the *why*, matching the existing style.

## Project layout

See the tree in [README.md](README.md) and the didactic guides in [`docs/`](docs/).
