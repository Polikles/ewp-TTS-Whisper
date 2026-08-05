"""Keep the MVP traceability matrix synchronized with normative requirement IDs."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENT_ID = re.compile(r"\b(?:FR-[A-I]\d+(?:\.\d+)?|NFR-\d{3})\b")


def test_traceability_matrix_covers_every_normative_requirement() -> None:
    requirements = (ROOT / "docs/02-requirements.md").read_text(encoding="utf-8")
    traceability = (ROOT / "docs/20-mvp-requirements-traceability.md").read_text(encoding="utf-8")

    expected = set(REQUIREMENT_ID.findall(requirements))
    traced = set(REQUIREMENT_ID.findall(traceability))

    assert traced == expected
