"""Tests for immutable revision models and canonical-base compatibility."""

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.domain.errors import InvalidRevisionError
from ewp_transcripts.domain.revision import (
    TranscriptRevision,
    load_transcript_revision,
    sha256_file,
    validate_revision_base,
)

ROOT = Path(__file__).resolve().parents[2]
REVISION_EXAMPLE = ROOT / "examples/revision.example.json"
RESULT_EXAMPLE = ROOT / "examples/results.example.json"


def _compatible_revision_data() -> dict:
    data = json.loads(REVISION_EXAMPLE.read_text(encoding="utf-8"))
    base_bytes = RESULT_EXAMPLE.read_bytes()
    data["job_id"] = "S01E01"
    data["base_result"] = {
        "job_id": "S01E01",
        "result_version": 1,
        "schema_version": "1.0",
        "sha256": hashlib.sha256(base_bytes).hexdigest(),
        "filename": RESULT_EXAMPLE.name,
    }
    return data


def _parse_revision(data: dict) -> TranscriptRevision:
    return TranscriptRevision.model_validate_json(json.dumps(data))


def test_revision_example_loads_as_frozen_domain_model() -> None:
    revision = load_transcript_revision(REVISION_EXAMPLE)

    assert revision.schema_version == "1.0"
    assert revision.transcript.tokens[-1].insertion_anchor is not None
    with pytest.raises(ValidationError):
        revision.revision_number = 2  # type: ignore[misc]


def test_revision_rejects_mapping_without_words_or_insertion_anchor() -> None:
    data = json.loads(REVISION_EXAMPLE.read_text(encoding="utf-8"))
    data["transcript"]["tokens"][-1].pop("insertion_anchor")

    with pytest.raises(ValidationError, match="inserted tokens require"):
        _parse_revision(data)


def test_revision_rejects_manual_llm_provenance() -> None:
    data = json.loads(REVISION_EXAMPLE.read_text(encoding="utf-8"))
    data["provenance"]["llm"] = {
        "provider": "example",
        "model": "example",
        "endpoint_kind": "local",
        "prompt_sha256": "a" * 64,
    }

    with pytest.raises(ValidationError, match="manual revisions cannot"):
        _parse_revision(data)


def test_compatible_revision_validates_against_exact_base() -> None:
    revision = _parse_revision(_compatible_revision_data())
    base = load_canonical_result(RESULT_EXAMPLE)

    validate_revision_base(revision, base, base_sha256=sha256_file(RESULT_EXAMPLE))


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data["base_result"].update(sha256="f" * 64), "SHA-256"),
        (
            lambda data: data["transcript"]["tokens"][0].update(source_word_ids=["word_999999"]),
            "unknown canonical word",
        ),
        (
            lambda data: data["transcript"]["tokens"][0].update(speaker_id="speaker_999"),
            "unknown speaker",
        ),
    ],
)
def test_revision_base_mismatch_is_rejected(mutation, message: str) -> None:
    data = _compatible_revision_data()
    mutation(data)
    revision = _parse_revision(data)
    base = load_canonical_result(RESULT_EXAMPLE)

    with pytest.raises(InvalidRevisionError, match=message):
        validate_revision_base(revision, base, base_sha256=sha256_file(RESULT_EXAMPLE))


def test_revision_rejects_out_of_order_source_mapping() -> None:
    data = _compatible_revision_data()
    data["transcript"]["tokens"][0]["source_word_ids"] = [
        "word_000002",
        "word_000001",
    ]
    revision = _parse_revision(data)
    base = load_canonical_result(RESULT_EXAMPLE)

    with pytest.raises(InvalidRevisionError, match="out of canonical order"):
        validate_revision_base(revision, base, base_sha256=sha256_file(RESULT_EXAMPLE))
