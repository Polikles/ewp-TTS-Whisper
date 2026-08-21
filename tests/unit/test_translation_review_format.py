"""Tests for EWP-TRANSLATION 1 rendering and parsing."""

from pathlib import Path

import pytest

from ewp_transcripts.domain.errors import InvalidTranslationError
from ewp_transcripts.translation_review_format import (
    parse_translation_review,
    render_translation_review,
)
from ewp_transcripts.translation_review_service import prepare_translation_review

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "examples/results.example.json"


def test_translation_review_round_trip_is_deterministic() -> None:
    review = prepare_translation_review(RESULT, target_language="pl")

    rendered = render_translation_review(review)
    parsed = parse_translation_review(rendered)

    assert parsed == review
    assert render_translation_review(parsed) == rendered
    assert rendered.startswith("EWP-TRANSLATION 1\n# metadata: ")


def test_target_line_is_editable() -> None:
    review = prepare_translation_review(RESULT, target_language="pl")
    rendered = render_translation_review(review)
    edited = rendered.replace("> \n", "> Witaj w kolejnym odcinku.\n", 1)

    parsed = parse_translation_review(edited)

    assert parsed.units[0].target_text == "Witaj w kolejnym odcinku."


def test_source_line_edit_is_rejected_by_hash() -> None:
    review = prepare_translation_review(RESULT, target_language="pl")
    rendered = render_translation_review(review)
    damaged = rendered.replace("< Welcome", "< Changed", 1)

    with pytest.raises(InvalidTranslationError, match="content is invalid"):
        parse_translation_review(damaged)
