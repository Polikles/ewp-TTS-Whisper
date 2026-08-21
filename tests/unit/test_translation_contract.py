"""Validate the translation schema and public example artifact."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from ewp_transcripts.domain.translation import TranscriptTranslation

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/translation.schema.json"
EXAMPLE_PATH = ROOT / "examples/translation.example.json"


def test_translation_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(
        json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    )


def test_translation_example_matches_schema_and_domain_model() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    serialized = EXAMPLE_PATH.read_text(encoding="utf-8")
    example = json.loads(serialized)

    Draft202012Validator(schema, format_checker=FormatChecker()).validate(example)
    translation = TranscriptTranslation.model_validate_json(serialized)

    assert translation.direction.source_language == "en"
    assert translation.direction.target_language == "pl"
    assert translation.source.verification == "raw"
    assert translation.statistics.unit_count == 2
