.PHONY: build check format lint test test-integration typecheck

check:
	./scripts/check.sh

lint:
	uv run --locked --no-sync ruff check src tests/unit tests/integration
	uv run --locked --no-sync ruff format --check src tests/unit tests/integration

format:
	uv run --locked --no-sync ruff check --fix src tests/unit tests/integration
	uv run --locked --no-sync ruff format src tests/unit tests/integration

typecheck:
	uv run --locked --no-sync mypy src

test:
	uv run --locked --no-sync pytest -q

test-integration:
	./scripts/test_integration.sh

build:
	uv build
