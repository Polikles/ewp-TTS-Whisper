"""Tests for strict canonical result parsing and semantic invariants."""

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from ewp_transcripts.domain.canonical import CanonicalResult, load_canonical_result

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/results.schema.json"
EXAMPLE_PATH = ROOT / "examples/results.example.json"


@pytest.fixture
def example() -> dict[str, Any]:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_loads_example_and_round_trips_through_authoritative_schema() -> None:
    result = load_canonical_result(EXAMPLE_PATH)
    dumped = result.model_dump(mode="json", exclude_none=False)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert result.episode.episode_id == "S01E01"
    assert len(result.transcript.segments) == 2
    assert list(Draft202012Validator(schema).iter_errors(dumped)) == []
    assert CanonicalResult.model_validate_json(result.model_dump_json()) == result


def test_rejects_undocumented_fields(example: dict[str, Any]) -> None:
    example["undocumented"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CanonicalResult.model_validate_json(json.dumps(example))


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda value: value["transcript"]["segments"][0].update(end_ms=2000),
            "word timestamps must fit inside their segment",
        ),
        (
            lambda value: value["transcript"]["segments"].reverse(),
            "segments must be sorted chronologically",
        ),
        (
            lambda value: value["transcript"]["segments"][0].update(speaker_id="speaker_999"),
            "transcript must reference known speakers",
        ),
        (
            lambda value: value.update(completed_at=None),
            "completed results require completed_at",
        ),
    ],
)
def test_rejects_semantically_inconsistent_results(
    example: dict[str, Any],
    mutation: Callable[[dict[str, Any]], object],
    message: str,
) -> None:
    invalid = copy.deepcopy(example)
    mutation(invalid)

    with pytest.raises(ValidationError, match=message):
        CanonicalResult.model_validate_json(json.dumps(invalid))
