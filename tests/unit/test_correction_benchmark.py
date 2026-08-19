"""Tests for exact-lineage automated-correction benchmark manifests."""

import hashlib
from pathlib import Path

import pytest

from ewp_transcripts.correction import (
    DeterministicMockCorrectionProvider,
    build_mock_correction_revision,
)
from ewp_transcripts.correction_benchmark import (
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
normalization = "ewp-phase0-lexical-v1"

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

    assert report["report_version"] == "ewp-correction-benchmark-v1"
    assert report["case_count"] == 1
    case = report["cases"][0]
    assert case["source_kind"] == source_kind
    assert case["candidate"]["wer"] == 0.0
    assert case["word_error_reduction"] == 1
    assert case["excess_word_errors"] == 0


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
