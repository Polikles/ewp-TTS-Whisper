#!/usr/bin/env bash
set -euo pipefail

uv run --locked --no-sync pytest -q -m integration tests/integration
