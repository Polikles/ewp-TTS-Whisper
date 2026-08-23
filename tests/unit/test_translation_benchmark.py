"""Tests for exact-lineage, human-scored semantic translation benchmarks."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ewp_transcripts.cli import app
from ewp_transcripts.translation_benchmark import (
    SemanticIssue,
    TranslationBenchmarkAssessment,
    TranslationUnitAssessment,
    evaluate_translation_benchmark,
    prepare_translation_benchmark_assessments,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/translation.example.json"


def _artifacts(tmp_path: Path) -> tuple[Path, Path]:
    candidates = tmp_path / "candidates"
    golds = tmp_path / "golds"
    candidates.mkdir()
    golds.mkdir()
    original = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    original["direction"] = {"source_language": "pl", "target_language": "en"}
    original["source"]["verification"] = "raw"
    candidate = json.loads(json.dumps(original))
    candidate["provenance"] = {
        "method": "llm",
        "interface": "api",
        "llm": {
            "provider": "mock",
            "model": "semantic-test",
            "endpoint_kind": "mock",
            "prompt_id": "translation-v1",
            "prompt_sha256": "a" * 64,
            "parameters": None,
        },
    }
    candidate["units"][0]["target_text"] = "Welcome to the next episode."
    candidate["units"][1]["target_text"] = "Today we discuss transcription."
    candidate["statistics"]["target_tokens"] = 9
    gold = json.loads(json.dumps(original))
    gold["translation_number"] = 2
    gold["units"][0]["target_text"] = "Welcome to another episode."
    gold["units"][1]["target_text"] = "Today we are talking about transcription."
    gold["statistics"]["target_tokens"] = 10
    (candidates / "episode_translation_001.json").write_text(
        json.dumps(candidate), encoding="utf-8"
    )
    (golds / "episode_translation_002.json").write_text(json.dumps(gold), encoding="utf-8")
    return candidates, golds


def _complete(path: Path) -> None:
    assessment = TranslationBenchmarkAssessment.model_validate_json(
        path.read_text(encoding="utf-8")
    )
    completed = assessment.model_copy(
        update={
            "units": (
                TranslationUnitAssessment(unit_id="tu_000001", semantic_status="faithful"),
                TranslationUnitAssessment(
                    unit_id="tu_000002",
                    semantic_status="major_error",
                    issues=(SemanticIssue(category="omission", severity="major"),),
                    convention_status="fail",
                    convention_violations=1,
                ),
            )
        }
    )
    path.write_text(completed.model_dump_json(indent=2) + "\n", encoding="utf-8")


def test_semantic_benchmark_requires_human_review_and_does_not_score_word_overlap(
    tmp_path: Path,
) -> None:
    candidates, golds = _artifacts(tmp_path)
    paths = prepare_translation_benchmark_assessments(
        candidate_directory=candidates, gold_directory=golds, output_directory=tmp_path / "bundle"
    )

    with pytest.raises(ValueError, match="incomplete"):
        evaluate_translation_benchmark(paths)
    _complete(paths[0])
    report = evaluate_translation_benchmark(paths)

    assert report["evaluation"] == "human semantic fidelity; no lexical-overlap quality score"
    assert report["direction"] == "pl->en"
    assert report["aggregate"] == {
        "unit_count": 2,
        "semantic_status_counts": {"faithful": 1, "major_error": 1},
        "semantic_issue_counts": {"omission": 1},
        "semantic_pass_rate": 0.5,
        "convention_status_counts": {"fail": 1, "not_applicable": 1},
        "convention_violations": 1,
    }


def test_semantic_benchmark_rejects_changed_candidate(tmp_path: Path) -> None:
    candidates, golds = _artifacts(tmp_path)
    paths = prepare_translation_benchmark_assessments(
        candidate_directory=candidates, gold_directory=golds, output_directory=tmp_path / "bundle"
    )
    _complete(paths[0])
    staged = tmp_path / "bundle/artifacts/candidate/episode_translation_001.json"
    staged.write_text("changed", encoding="utf-8")

    with pytest.raises(ValueError, match="candidate SHA-256 mismatch"):
        evaluate_translation_benchmark(paths)


def test_semantic_benchmark_rejects_assessment_direction_mismatch(tmp_path: Path) -> None:
    candidates, golds = _artifacts(tmp_path)
    paths = prepare_translation_benchmark_assessments(
        candidate_directory=candidates, gold_directory=golds, output_directory=tmp_path / "bundle"
    )
    _complete(paths[0])
    second = TranslationBenchmarkAssessment.model_validate_json(
        paths[0].read_text(encoding="utf-8")
    )
    second_path = tmp_path / "bundle/other_semantic_assessment.json"
    second_path.write_text(
        second.model_copy(
            update={"case_id": "other", "source_language": "en", "target_language": "pl"}
        ).model_dump_json(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="direction differs"):
        evaluate_translation_benchmark((paths[0], second_path))


def test_translation_benchmark_cli_prepares_and_reports(tmp_path: Path) -> None:
    candidates, golds = _artifacts(tmp_path)
    bundle = tmp_path / "bundle"
    runner = CliRunner()
    prepared = runner.invoke(
        app,
        [
            "benchmark",
            "translation",
            "prepare",
            str(candidates),
            "--gold-dir",
            str(golds),
            "--output-dir",
            str(bundle),
        ],
    )
    assessment = bundle / "S01E01_semantic_assessment.json"
    _complete(assessment)
    report_path = tmp_path / "report.json"
    reported = runner.invoke(
        app,
        ["benchmark", "translation", "report", str(bundle), "--output", str(report_path)],
    )

    assert prepared.exit_code == reported.exit_code == 0
    assert "pending_review=1" in prepared.stdout
    assert "semantic_pass_rate=0.50000000" in reported.stdout
    assert json.loads(report_path.read_text(encoding="utf-8"))["direction"] == "pl->en"
