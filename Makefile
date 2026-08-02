.PHONY: build check format lint test typecheck

check:
	./scripts/check.sh

lint:
	uv run --locked --no-sync ruff check src tests/unit
	uv run --locked --no-sync ruff format --check src tests/unit

format:
	uv run --locked --no-sync ruff check --fix src tests/unit
	uv run --locked --no-sync ruff format src tests/unit

typecheck:
	uv run --locked --no-sync mypy src

test:
	uv run --locked --no-sync pytest -q

build:
	uv build
