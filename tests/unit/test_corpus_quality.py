"""Tests for strict manifest-driven corpus aggregation."""

import hashlib
import json
from pathlib import Path

import pytest

from ewp_transcripts.corpus_quality import evaluate_corpus, load_corpus_manifest


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(tmp_path: Path, reference_hash: str) -> Path:
    path = tmp_path / "manifest.toml"
    path.write_text(
        f'''manifest_version = "1.0"
normalization = "ewp-phase0-lexical-v1"

[[cases]]
case_id = "P0-01"
language = "pl"
reference_path = "references/p0-01.txt"
reference_sha256 = "{reference_hash}"
hypothesis_path = "p0-01_results.json"
hypothesis_format = "auto"
''',
        encoding="utf-8",
    )
    return path


def test_evaluate_corpus_reports_per_case_macro_micro_and_error_diff(tmp_path: Path) -> None:
    references = tmp_path / "references"
    hypotheses = tmp_path / "hypotheses"
    references.mkdir()
    hypotheses.mkdir()
    reference = references / "p0-01.txt"
    reference.write_text("Ala ma dwa koty.", encoding="utf-8")
    hypothesis = hypotheses / "p0-01_results.json"
    hypothesis.write_text(
        json.dumps({"transcript": {"segments": [{"text": "Ala ma trzy koty."}]}}),
        encoding="utf-8",
    )
    manifest = load_corpus_manifest(_manifest(tmp_path, _sha256(reference)))

    report, difference = evaluate_corpus(manifest, hypothesis_root=hypotheses)

    assert report["report_version"] == "ewp-corpus-quality-v1"
    assert report["case_count"] == 1
    case = report["cases"][0]
    assert case["wer"] == 0.25
    assert case["hypothesis_format"] == "canonical-json"
    assert report["aggregate"]["macro_average"]["wer"] == 0.25
    assert report["aggregate"]["micro_average"]["wer"] == 0.25
    assert difference == "## P0-01\n~ dwa -> trzy\n"


def test_evaluate_corpus_rejects_changed_reference(tmp_path: Path) -> None:
    references = tmp_path / "references"
    hypotheses = tmp_path / "hypotheses"
    references.mkdir()
    hypotheses.mkdir()
    reference = references / "p0-01.txt"
    reference.write_text("changed", encoding="utf-8")
    (hypotheses / "p0-01_results.json").write_text("{}", encoding="utf-8")
    manifest = load_corpus_manifest(_manifest(tmp_path, "0" * 64))

    with pytest.raises(ValueError, match="Reference SHA-256 mismatch"):
        evaluate_corpus(manifest, hypothesis_root=hypotheses)


def test_manifest_rejects_parent_path_escape(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, "0" * 64)
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            'reference_path = "references/p0-01.txt"',
            'reference_path = "../reference.txt"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="safe relative paths"):
        load_corpus_manifest(manifest)
