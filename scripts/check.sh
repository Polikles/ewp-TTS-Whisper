#!/usr/bin/env bash
set -euo pipefail

uv run --locked --no-sync ruff check src tests/unit tests/integration
uv run --locked --no-sync ruff format --check src tests/unit tests/integration
uv run --locked --no-sync mypy src
uv run --locked --no-sync pytest -q
