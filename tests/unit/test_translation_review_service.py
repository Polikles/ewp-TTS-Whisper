"""Tests for exact-lineage manual translation review preparation."""

from pathlib import Path

import pytest

from ewp_transcripts.domain.errors import InvalidTranslationError
from ewp_transcripts.translation_review_service import (
    prepare_translation_review,
    validate_translation_review_source,
)

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "examples/results.example.json"


def test_prepare_raw_translation_review_has_blank_targets_and_exact_coverage() -> None:
    review = prepare_translation_review(RESULT, target_language="pl")

    assert review.header.source_language == "en"
    assert review.header.target_language == "pl"
    assert review.header.source.verification == "raw"
    assert review.header.style.register_mode == "preserve"
    assert all(not unit.target_text for unit in review.units)
    token_ids = [token_id for unit in review.units for token_id in unit.source_token_ids]
    assert token_ids == [f"word_{index:06d}" for index in range(1, 9)]


def test_prepare_rejects_same_target_language() -> None:
    with pytest.raises(ValueError, match="must differ"):
        prepare_translation_review(RESULT, target_language="en")


def test_validate_review_source_accepts_only_target_edits() -> None:
    review = prepare_translation_review(RESULT, target_language="pl")
    edited = review.model_copy(
        update={
            "units": tuple(
                unit.model_copy(update={"target_text": "Przetłumaczone."}) for unit in review.units
            )
        }
    )

    validate_translation_review_source(edited, RESULT)


def test_validate_review_source_rejects_machine_owned_changes() -> None:
    review = prepare_translation_review(RESULT, target_language="pl")
    changed = review.units[0].model_copy(update={"speaker_id": "speaker_999"})
    units = (changed, *review.units[1:])

    with pytest.raises(InvalidTranslationError, match="units do not match"):
        validate_translation_review_source(review.model_copy(update={"units": units}), RESULT)
