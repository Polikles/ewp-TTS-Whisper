"""Contract tests for the authoritative canonical result schema and example."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ewp_transcripts.domain.canonical import load_canonical_result

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/results.schema.json"
EXAMPLE_PATH = ROOT / "examples/results.example.json"


def test_results_schema_is_valid_draft_2020_12() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator.check_schema(schema)


def test_canonical_example_satisfies_results_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    example = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )

    assert list(validator.iter_errors(example)) == []


def test_legacy_result_without_segment_kind_defaults_to_speech() -> None:
    result = load_canonical_result(EXAMPLE_PATH)

    assert {segment.kind for segment in result.transcript.segments} == {"speech"}


def test_unknown_segment_kind_is_rejected(tmp_path: Path) -> None:
    document = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    document["transcript"]["segments"][0]["kind"] = "applause"
    path = tmp_path / "invalid_results.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="kind"):
        load_canonical_result(path)
