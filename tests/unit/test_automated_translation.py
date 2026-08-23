"""Tests for provider-neutral automated translation."""

from pathlib import Path

import pytest

from ewp_transcripts.automated_translation import (
    DeterministicMockTranslationProvider,
    build_automated_translation,
    build_automated_translation_request,
    validate_automated_translation_response,
)
from ewp_transcripts.domain.automated_translation import AutomatedTranslationResponse
from ewp_transcripts.domain.errors import InvalidTranslationResponseError
from ewp_transcripts.translation_review_service import prepare_translation_review

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def test_request_owns_one_unit_and_context_is_read_only() -> None:
    review = prepare_translation_review(EXAMPLE, target_language="pl")
    provider = DeterministicMockTranslationProvider()

    request = build_automated_translation_request(review, 1, provider=provider, context_units=1)

    assert request.unit.unit_id == review.units[1].unit_id
    assert tuple(unit.unit_id for unit in request.preceding_context) == (review.units[0].unit_id,)
    assert request.following_context == ()
    assert len(request.operation_id) == 64


def test_response_must_match_operation_and_owned_unit() -> None:
    review = prepare_translation_review(EXAMPLE, target_language="pl")
    provider = DeterministicMockTranslationProvider()
    request = build_automated_translation_request(review, 0, provider=provider)

    with pytest.raises(InvalidTranslationResponseError, match="operation ID"):
        validate_automated_translation_response(
            request,
            AutomatedTranslationResponse(
                operation_id="0" * 64,
                unit_id=request.unit.unit_id,
                target_text="Translated.",
            ),
        )


def test_builds_non_final_llm_candidate_with_exact_unit_lineage(tmp_path: Path) -> None:
    provider = DeterministicMockTranslationProvider(
        {"tu_000001": "Welcome to another episode.", "tu_000002": "Transcription today."}
    )

    translation = build_automated_translation(
        EXAMPLE,
        provider,
        target_language="pl",
        resume_directory=tmp_path / "state",
    )
    repeated = build_automated_translation(
        EXAMPLE,
        provider,
        target_language="pl",
        resume_directory=tmp_path / "state",
    )

    assert translation.provenance.method == "llm"
    assert translation.provenance.llm is not None
    assert translation.provenance.llm.provider == "ewp-mock-translation"
    assert translation.source.verification == "raw"
    assert [unit.target_text for unit in translation.units] == [
        "Welcome to another episode.",
        "Transcription today.",
    ]
    assert [unit.source_token_ids for unit in repeated.units] == [
        unit.source_token_ids for unit in translation.units
    ]
    assert len(tuple((tmp_path / "state").glob("*.json"))) == 2
