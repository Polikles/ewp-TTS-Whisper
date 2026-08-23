"""Tests for the manual translation CLI vertical slice."""

import json
from pathlib import Path

from typer.testing import CliRunner

from ewp_transcripts.cli import _warn_unreviewed_translation_source, app
from ewp_transcripts.translation_review_format import (
    load_translation_review,
    render_translation_review,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"
runner = CliRunner()


def test_unreviewed_translation_source_warning_is_explicit(capsys) -> None:  # type: ignore[no-untyped-def]
    _warn_unreviewed_translation_source("automated_candidate")

    assert "unreviewed automated transcript candidate" in capsys.readouterr().err


def _prepare_completed_review(tmp_path: Path) -> tuple[Path, Path]:
    results = tmp_path / "results.example.json"
    results.write_bytes(EXAMPLE.read_bytes())
    reviews = tmp_path / "reviews"
    prepared = runner.invoke(
        app,
        [
            "translate",
            "prepare",
            str(results),
            "--target-language",
            "pl",
            "--output-dir",
            str(reviews),
        ],
    )
    assert prepared.exit_code == 0, prepared.stdout
    review_path = reviews / "S01E01_pl.translation.review.txt"
    review = load_translation_review(review_path)
    completed = review.model_copy(
        update={
            "units": tuple(
                unit.model_copy(update={"target_text": f"Tłumaczenie {index}."})
                for index, unit in enumerate(review.units, start=1)
            )
        }
    )
    review_path.write_text(render_translation_review(completed), encoding="utf-8")
    return results, review_path


def test_translate_help_exposes_manual_workflow() -> None:
    result = runner.invoke(app, ["translate", "--help"])

    assert result.exit_code == 0
    assert "prepare" in result.stdout
    assert "preview" in result.stdout
    assert "apply" in result.stdout
    assert "export" in result.stdout
    assert "audit" in result.stdout


def test_prepare_preview_and_apply_translation(tmp_path: Path) -> None:
    results, review = _prepare_completed_review(tmp_path)
    preview = runner.invoke(
        app,
        ["translate", "preview", str(review), "--results", str(results)],
    )
    translations = tmp_path / "translations"
    applied = runner.invoke(
        app,
        [
            "translate",
            "apply",
            str(review),
            "--results",
            str(results),
            "--output-dir",
            str(translations),
            "--json-output",
        ],
    )

    assert preview.exit_code == 0, preview.stdout
    assert "SUMMARY units=" in preview.stdout
    assert applied.exit_code == 0, applied.stdout
    payload = json.loads(applied.stdout)
    assert payload["translation_number"] == 1
    assert Path(payload["translation_path"]).name == "S01E01_pl_translation_001.json"


def test_preview_rejects_blank_target(tmp_path: Path) -> None:
    results = tmp_path / "results.example.json"
    results.write_bytes(EXAMPLE.read_bytes())
    reviews = tmp_path / "reviews"
    prepared = runner.invoke(
        app,
        [
            "translate",
            "prepare",
            str(results),
            "--target-language",
            "pl",
            "--output-dir",
            str(reviews),
        ],
    )
    assert prepared.exit_code == 0

    preview = runner.invoke(
        app,
        [
            "translate",
            "preview",
            str(reviews / "S01E01_pl.translation.review.txt"),
            "--results",
            str(results),
        ],
    )

    assert preview.exit_code == 4
    assert "untranslated unit" in preview.stderr


def test_translation_directory_prepare_preview_and_apply(tmp_path: Path) -> None:
    results = tmp_path / "results"
    reviews = tmp_path / "reviews"
    translations = tmp_path / "translations"
    results.mkdir()
    result_path = results / "episode_results.json"
    result_path.write_bytes(EXAMPLE.read_bytes())

    prepared = runner.invoke(
        app,
        [
            "translate",
            "prepare",
            str(results),
            "--target-language",
            "pl",
            "--output-dir",
            str(reviews),
        ],
    )
    assert prepared.exit_code == 0, prepared.stdout
    assert "SUMMARY prepared=1" in prepared.stdout
    review_path = reviews / "S01E01_pl.translation.review.txt"
    review = load_translation_review(review_path)
    completed = review.model_copy(
        update={
            "units": tuple(
                unit.model_copy(update={"target_text": f"Cel {index}."})
                for index, unit in enumerate(review.units, start=1)
            )
        }
    )
    review_path.write_text(render_translation_review(completed), encoding="utf-8")

    previewed = runner.invoke(
        app,
        ["translate", "preview", str(reviews), "--results", str(results)],
    )
    applied = runner.invoke(
        app,
        [
            "translate",
            "apply",
            str(reviews),
            "--results",
            str(results),
            "--output-dir",
            str(translations),
        ],
    )

    assert previewed.exit_code == 0, previewed.stdout
    assert "SUMMARY prepared=0 previewed=1" in previewed.stdout
    assert applied.exit_code == 0, applied.stdout
    assert "SUMMARY prepared=0 previewed=0 applied=1" in applied.stdout
    assert (translations / "S01E01_pl_translation_001.json").is_file()


def test_translate_export_writes_txt(tmp_path: Path) -> None:
    output = tmp_path / "output"

    result = runner.invoke(
        app,
        [
            "translate",
            "export",
            str(ROOT / "examples/translation.example.json"),
            "--output-dir",
            str(output),
            "--format",
            "txt",
            "--format",
            "srt",
            "--format",
            "vtt",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "WROTE" in result.stdout
    assert (output / "S01E01_pl_translation_001.txt").is_file()
    assert (output / "S01E01_pl_translation_001.srt").is_file()
    assert (output / "S01E01_pl_translation_001.vtt").is_file()


def test_translate_export_directory_reports_batch(tmp_path: Path) -> None:
    translations = tmp_path / "translations"
    output = tmp_path / "output"
    translations.mkdir()
    (translations / "S01E01_pl_translation_001.json").write_bytes(
        (ROOT / "examples/translation.example.json").read_bytes()
    )

    result = runner.invoke(
        app,
        ["translate", "export", str(translations), "--output-dir", str(output)],
    )

    assert result.exit_code == 0, result.stdout
    assert "SUMMARY exported=1 failed=0" in result.stdout
    assert (output / "S01E01_pl_translation_001.txt").is_file()


def test_translate_audit_reconstructs_and_writes(tmp_path: Path) -> None:
    output = tmp_path / "audits"

    result = runner.invoke(
        app,
        [
            "translate",
            "audit",
            str(ROOT / "examples/translation.example.json"),
            "--results-dir",
            str(ROOT / "examples"),
            "--output-dir",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "SUMMARY units=2 written=1" in result.stdout
    assert (output / "translation.example_audit.json").is_file()
