"""Tests for exact-lineage automated-correction benchmark manifests."""

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ewp_transcripts.cli import app
from ewp_transcripts.correction import (
    DeterministicMockCorrectionProvider,
    build_mock_correction_revision,
)
from ewp_transcripts.correction_benchmark import (
    build_correction_benchmark_bundle,
    evaluate_correction_benchmark,
    load_correction_benchmark_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_revision(path: Path, revision_number: int, *, corrected: bool) -> None:
    provider = DeterministicMockCorrectionProvider(
        {"transcription.": ("OpenAI.", "proper_name")} if corrected else {}
    )
    revision = build_mock_correction_revision(path.parent / "base_results.json", provider)
    revision = revision.model_copy(update={"revision_number": revision_number})
    path.write_text(revision.model_dump_json(indent=2), encoding="utf-8")


def _manifest(tmp_path: Path, *, source_kind: str = "canonical") -> Path:
    base = tmp_path / "base_results.json"
    base.write_bytes(EXAMPLE.read_bytes())
    source = base if source_kind == "canonical" else tmp_path / "source_revision.json"
    if source_kind == "revision":
        _write_revision(source, 1, corrected=False)
    candidate = tmp_path / "candidate_revision.json"
    gold = tmp_path / "gold_revision.json"
    _write_revision(candidate, 2, corrected=True)
    _write_revision(gold, 2, corrected=True)
    manifest = tmp_path / "correction-benchmark.toml"
    manifest.write_text(
        f'''manifest_version = "1.0"
normalization = "ewp-correction-lexical-v2"

[[cases]]
case_id = "episode-1"
base_path = "{base.name}"
base_sha256 = "{_sha(base)}"
source_kind = "{source_kind}"
source_path = "{source.name}"
source_sha256 = "{_sha(source)}"
candidate_path = "{candidate.name}"
candidate_sha256 = "{_sha(candidate)}"
gold_path = "{gold.name}"
gold_sha256 = "{_sha(gold)}"
''',
        encoding="utf-8",
    )
    return manifest


@pytest.mark.parametrize("source_kind", ["canonical", "revision"])
def test_benchmark_validates_both_lineage_tasks(tmp_path: Path, source_kind: str) -> None:
    manifest = load_correction_benchmark_manifest(_manifest(tmp_path, source_kind=source_kind))

    report = evaluate_correction_benchmark(manifest)

    assert report["report_version"] == "ewp-correction-benchmark-v4"
    assert report["case_count"] == 1
    case = report["cases"][0]
    assert case["source_kind"] == source_kind
    assert case["candidate"]["wer"] == 0.0
    assert case["source_to_candidate"]["word_errors"]["errors"] == 1
    assert case["word_error_reduction"] == 1
    assert case["excess_word_errors"] == 0
    assert case["lexical_outcome"] == "improved"
    assert case["candidate_revision_statistics"]["substitutions"] == 1
    assert case["candidate_warning_count"] == 0
    assert report["aggregate"]["baseline"]["word_errors"] == 1
    assert report["aggregate"]["source_to_candidate"]["word_errors"] == 1
    assert report["aggregate"]["candidate"]["word_errors"] == 0
    assert report["aggregate"]["lexical_correction"] == {
        "word_error_reduction": 1,
        "relative_word_error_reduction": 1.0,
        "candidate_word_changes": 1,
        "net_correction_efficiency": 1.0,
        "improved_cases": 1,
        "unchanged_cases": 0,
        "regressed_cases": 0,
    }
    assert report["aggregate"]["revision_activity"] == {
        "source_tokens": 8,
        "revision_tokens": 8,
        "unchanged": 7,
        "substitutions": 1,
        "merges": 0,
        "splits": 0,
        "insertions": 0,
        "deletions": 0,
        "punctuation_only_changes": 0,
        "speaker_changes": 0,
        "alignment_warnings": 0,
        "total_changes": 1,
        "warning_count": 0,
    }


def test_benchmark_rejects_changed_candidate(tmp_path: Path) -> None:
    manifest = load_correction_benchmark_manifest(_manifest(tmp_path))
    (tmp_path / "candidate_revision.json").write_text("changed", encoding="utf-8")

    with pytest.raises(ValueError, match="candidate SHA-256 mismatch"):
        evaluate_correction_benchmark(manifest)


def test_benchmark_rejects_parent_path_escape(tmp_path: Path) -> None:
    path = _manifest(tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            'candidate_path = "candidate_revision.json"',
            'candidate_path = "../candidate_revision.json"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="safe relative"):
        load_correction_benchmark_manifest(path)


def test_bundle_builder_selects_latest_compatible_gold_and_stages_private_files(
    tmp_path: Path,
) -> None:
    bases = tmp_path / "bases"
    candidates = tmp_path / "candidates"
    gold = tmp_path / "gold"
    for directory in (bases, candidates, gold):
        directory.mkdir()
    base = bases / "base_results.json"
    base.write_bytes(EXAMPLE.read_bytes())
    (candidates / "base_results.json").write_bytes(EXAMPLE.read_bytes())
    (gold / "base_results.json").write_bytes(EXAMPLE.read_bytes())
    _write_revision(candidates / "episode_revision_001.json", 1, corrected=True)
    _write_revision(gold / "episode_revision_001.json", 1, corrected=False)
    _write_revision(gold / "episode_revision_002.json", 2, corrected=True)

    manifest_path = build_correction_benchmark_bundle(
        base_directory=bases,
        candidate_directory=candidates,
        gold_directory=gold,
        output_directory=tmp_path / "bundle",
    )
    manifest = load_correction_benchmark_manifest(manifest_path)
    report = evaluate_correction_benchmark(manifest)

    assert manifest.cases[0].gold_path.name == "episode_revision_002.json"
    assert report["case_count"] == 1
    assert manifest_path.stat().st_mode & 0o777 == 0o600
    for path in (tmp_path / "bundle" / "artifacts").rglob("*.json"):
        assert path.stat().st_mode & 0o777 == 0o600


def test_correction_benchmark_cli_builds_and_reports_bundle(tmp_path: Path) -> None:
    bases = tmp_path / "bases"
    candidates = tmp_path / "candidates"
    gold = tmp_path / "gold"
    for directory in (bases, candidates, gold):
        directory.mkdir()
        (directory / "base_results.json").write_bytes(EXAMPLE.read_bytes())
    _write_revision(candidates / "episode_revision_001.json", 1, corrected=True)
    _write_revision(gold / "episode_revision_002.json", 2, corrected=True)
    bundle = tmp_path / "bundle"
    report = tmp_path / "report.json"
    runner = CliRunner()

    built = runner.invoke(
        app,
        [
            "benchmark",
            "correction",
            "build",
            str(bases),
            "--candidate-dir",
            str(candidates),
            "--gold-dir",
            str(gold),
            "--output-dir",
            str(bundle),
        ],
    )
    scored = runner.invoke(
        app,
        [
            "benchmark",
            "correction",
            "report",
            str(bundle / "manifest.toml"),
            "--output",
            str(report),
        ],
    )

    assert built.exit_code == scored.exit_code == 0
    assert "SUMMARY cases=1" in built.stdout
    assert "gold_llm_wer=0.00000000" in scored.stdout
    assert json.loads(report.read_text(encoding="utf-8"))["case_count"] == 1


def test_correction_benchmark_ignores_balanced_review_annotations(tmp_path: Path) -> None:
    manifest = load_correction_benchmark_manifest(_manifest(tmp_path))
    gold_path = tmp_path / "gold_revision.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    gold["transcript"]["tokens"][0]["text"] += " (speaker correction [editor note])"
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    manifest_path = tmp_path / "correction-benchmark.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace(
            manifest.cases[0].gold_sha256, _sha(gold_path)
        ),
        encoding="utf-8",
    )

    report = evaluate_correction_benchmark(load_correction_benchmark_manifest(manifest_path))

    assert report["cases"][0]["candidate"]["wer"] == 0.0
