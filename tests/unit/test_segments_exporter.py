"""Tests for the optional lightweight segments export."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.exporters.segments import render_segments_json

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = ROOT / "examples/results.example.json"
SCHEMA_PATH = ROOT / "schemas/segments.schema.json"
RESULTS_SHA256 = "a" * 64


def test_segments_export_satisfies_schema_and_records_provenance() -> None:
    result = load_canonical_result(EXAMPLE_PATH)

    rendered = render_segments_json(
        result,
        results_file="elsewhere/S01E01_results.json",
        results_sha256=RESULTS_SHA256,
        generated_at=datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
    )
    document = json.loads(rendered)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert list(Draft202012Validator(schema).iter_errors(document)) == []
    assert document["derived_from"] == {
        "results_file": "S01E01_results.json",
        "results_sha256": RESULTS_SHA256,
        "results_schema_version": "1.0",
    }
    assert document["generated_at"] == "2026-08-03T12:00:00Z"


def test_segments_export_merges_consecutive_canonical_segments_in_one_turn() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    second = result.transcript.segments[1].model_copy(
        update={
            "speaker_id": "speaker_001",
            "active_speaker_ids": ("speaker_001",),
        }
    )
    result = result.model_copy(
        update={
            "transcript": result.transcript.model_copy(
                update={"segments": (result.transcript.segments[0], second)}
            )
        }
    )

    document = json.loads(
        render_segments_json(
            result,
            results_file="S01E01_results.json",
            results_sha256=RESULTS_SHA256,
            generated_at=datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
        )
    )

    assert len(document["segments"]) == 1
    assert document["segments"][0]["text"] == (
        "Welcome to another episode. Today we discuss transcription."
    )
    assert len(document["segments"][0]["word_ids"]) == 8


def test_segments_export_can_omit_word_ids() -> None:
    result = load_canonical_result(EXAMPLE_PATH)

    document = json.loads(
        render_segments_json(
            result,
            results_file="S01E01_results.json",
            results_sha256=RESULTS_SHA256,
            generated_at=datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
            include_words=False,
        )
    )

    assert document["segmentation"]["include_words"] is False
    assert all(segment["word_ids"] == [] for segment in document["segments"])


def test_segments_export_rejects_invalid_provenance() -> None:
    result = load_canonical_result(EXAMPLE_PATH)

    with pytest.raises(ValueError, match="results_sha256"):
        render_segments_json(
            result,
            results_file="S01E01_results.json",
            results_sha256="not-a-hash",
            generated_at=datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        render_segments_json(
            result,
            results_file="S01E01_results.json",
            results_sha256=RESULTS_SHA256,
            generated_at=datetime(2026, 8, 3, 12, 0),
        )
