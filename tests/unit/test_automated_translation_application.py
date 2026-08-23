"""Application and CLI tests for automated translation candidates."""

import json
from pathlib import Path

from typer.testing import CliRunner

from ewp_transcripts.application import (
    apply_automated_translation,
    apply_translation_review_file,
    prepare_translation_review_file,
    preview_automated_translation,
    process_automated_translation_batch,
)
from ewp_transcripts.automated_translation import DeterministicMockTranslationProvider
from ewp_transcripts.cli import app
from ewp_transcripts.config import load_config

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def test_application_preview_is_write_free_and_apply_is_immutable(tmp_path: Path) -> None:
    provider = DeterministicMockTranslationProvider()

    preview = preview_automated_translation(
        EXAMPLE,
        config=load_config(),
        provider=provider,
        target_language="pl",
        resume_directory=tmp_path / "state",
    )
    applied = apply_automated_translation(
        EXAMPLE,
        config=load_config(),
        provider=provider,
        target_language="pl",
        resume_directory=tmp_path / "state",
        output_directory=tmp_path / "translations",
    )

    assert preview.translation_path is None
    assert applied.translation_path is not None
    assert applied.translation_path.name == "S01E01_pl_translation_001.json"
    assert applied.translation.provenance.method == "llm"


def test_cli_warns_that_mock_candidate_is_non_final(tmp_path: Path) -> None:
    runner = CliRunner()

    outcome = runner.invoke(
        app,
        [
            "translate",
            "automate",
            str(EXAMPLE),
            "--target-language",
            "pl",
            "--output-dir",
            str(tmp_path / "translations"),
            "--resume-dir",
            str(tmp_path / "state"),
        ],
    )

    assert outcome.exit_code == 0
    assert "non-final review candidate" in outcome.stderr
    assert "final=false" in outcome.stdout
    assert (tmp_path / "translations/S01E01_pl_translation_001.json").is_file()


def test_cli_uses_only_explicit_job_scoped_translation_dictionary(tmp_path: Path) -> None:
    dictionary = tmp_path / "dictionary.json"
    dictionary.write_text(
        json.dumps(
            {
                "dictionary_version": "1.0",
                "dictionary_id": "example-pl",
                "project_id": "example",
                "job_ids": ["S01E01"],
                "source_language": "en",
                "target_language": "pl",
                "entries": [{"source": "OpenAI", "target": "OpenAI"}],
            }
        ),
        encoding="utf-8",
    )
    outcome = CliRunner().invoke(
        app,
        [
            "translate",
            "automate",
            str(EXAMPLE),
            "--target-language",
            "pl",
            "--dictionary",
            str(dictionary),
            "--output-dir",
            str(tmp_path / "translations"),
            "--resume-dir",
            str(tmp_path / "state"),
        ],
    )

    assert outcome.exit_code == 0
    artifact = json.loads(
        (tmp_path / "translations/S01E01_pl_translation_001.json").read_text(encoding="utf-8")
    )
    parameters = artifact["provenance"]["llm"]["parameters"]
    assert parameters["dictionary_id"] == "example-pl"
    assert len(parameters["dictionary_sha256"]) == 64
    assert artifact["dictionary"] == {
        "dictionary_version": "1.0",
        "dictionary_id": "example-pl",
        "project_id": "example",
        "sha256": parameters["dictionary_sha256"],
    }


def test_automated_batch_isolates_invalid_results(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    (results / "valid_results.json").write_bytes(EXAMPLE.read_bytes())
    (results / "invalid_results.json").write_text("not json", encoding="utf-8")

    outcome = process_automated_translation_batch(
        results,
        config=load_config(),
        provider=DeterministicMockTranslationProvider(),
        target_language="pl",
        resume_directory=tmp_path / "state",
        output_directory=tmp_path / "translations",
    )

    assert outcome.count("published") == 1
    assert outcome.count("failed") == 1
    assert not outcome.stopped_early


def test_automated_candidate_can_become_an_exact_manual_child(tmp_path: Path) -> None:
    config = load_config()
    candidate = apply_automated_translation(
        EXAMPLE,
        config=config,
        provider=DeterministicMockTranslationProvider(),
        target_language="pl",
        output_directory=tmp_path / "translations",
    )
    assert candidate.translation_path is not None
    prepared = prepare_translation_review_file(
        EXAMPLE,
        target_language="pl",
        config=config,
        parent_translation_path=candidate.translation_path,
        output_directory=tmp_path / "reviews",
    )

    accepted = apply_translation_review_file(
        prepared.path,
        result_path=EXAMPLE,
        config=config,
        parent_translation_path=candidate.translation_path,
        output_directory=tmp_path / "translations",
    )

    assert all(unit.target_text for unit in prepared.review.units)
    assert accepted.translation.provenance.method == "manual"
    assert accepted.translation.parent_translation is not None
    assert (
        accepted.translation.parent_translation.translation_id
        == candidate.translation.translation_id
    )
    assert accepted.translation_path.name == "S01E01_pl_translation_002.json"
