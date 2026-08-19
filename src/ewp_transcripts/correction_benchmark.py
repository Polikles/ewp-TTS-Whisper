"""Exact-lineage lexical benchmarks for automated transcript correction."""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from ewp_transcripts.domain.canonical import CanonicalResult, load_canonical_result
from ewp_transcripts.domain.revision import (
    TranscriptRevision,
    load_transcript_revision,
    validate_revision_base,
)
from ewp_transcripts.quality import NORMALIZATION_VERSION, score

SourceKind = Literal["canonical", "revision"]


@dataclass(frozen=True, slots=True)
class CorrectionBenchmarkCase:
    case_id: str
    base_path: Path
    base_sha256: str
    source_kind: SourceKind
    source_path: Path
    source_sha256: str
    candidate_path: Path
    candidate_sha256: str
    gold_path: Path
    gold_sha256: str


@dataclass(frozen=True, slots=True)
class CorrectionBenchmarkManifest:
    path: Path
    cases: tuple[CorrectionBenchmarkCase, ...]


def load_correction_benchmark_manifest(path: Path) -> CorrectionBenchmarkManifest:
    """Load a strict path-safe correction benchmark manifest."""

    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ValueError("Cannot read correction benchmark manifest") from error
    if set(document) != {"manifest_version", "normalization", "cases"}:
        raise ValueError("Correction benchmark manifest has undocumented root fields")
    if document["manifest_version"] != "1.0":
        raise ValueError("Unsupported correction benchmark manifest version")
    if document["normalization"] != NORMALIZATION_VERSION:
        raise ValueError("Correction benchmark normalization does not match")
    raw_cases = document["cases"]
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("Correction benchmark manifest requires cases")
    expected = {
        "case_id",
        "base_path",
        "base_sha256",
        "source_kind",
        "source_path",
        "source_sha256",
        "candidate_path",
        "candidate_sha256",
        "gold_path",
        "gold_sha256",
    }
    cases: list[CorrectionBenchmarkCase] = []
    seen: set[str] = set()
    for raw in raw_cases:
        if not isinstance(raw, dict) or set(raw) != expected:
            raise ValueError("Correction benchmark case fields do not match the contract")
        case_id = _string(raw, "case_id")
        if case_id in seen:
            raise ValueError(f"Duplicate correction benchmark case: {case_id}")
        seen.add(case_id)
        source_kind = _string(raw, "source_kind")
        if source_kind not in {"canonical", "revision"}:
            raise ValueError(f"Invalid correction benchmark source kind: {case_id}")
        cases.append(
            CorrectionBenchmarkCase(
                case_id=case_id,
                base_path=_relative(raw, "base_path"),
                base_sha256=_sha_field(raw, "base_sha256"),
                source_kind=cast(SourceKind, source_kind),
                source_path=_relative(raw, "source_path"),
                source_sha256=_sha_field(raw, "source_sha256"),
                candidate_path=_relative(raw, "candidate_path"),
                candidate_sha256=_sha_field(raw, "candidate_sha256"),
                gold_path=_relative(raw, "gold_path"),
                gold_sha256=_sha_field(raw, "gold_sha256"),
            )
        )
    return CorrectionBenchmarkManifest(path=path, cases=tuple(cases))


def evaluate_correction_benchmark(
    manifest: CorrectionBenchmarkManifest,
) -> dict[str, object]:
    """Verify exact artifact lineage and report lexical correction quality."""

    reports: list[dict[str, object]] = []
    for case in manifest.cases:
        root = manifest.path.parent
        base_path = root / case.base_path
        source_path = root / case.source_path
        candidate_path = root / case.candidate_path
        gold_path = root / case.gold_path
        _require_hash(base_path, case.base_sha256, case.case_id, "base")
        _require_hash(source_path, case.source_sha256, case.case_id, "source")
        _require_hash(candidate_path, case.candidate_sha256, case.case_id, "candidate")
        _require_hash(gold_path, case.gold_sha256, case.case_id, "gold")
        base = load_canonical_result(base_path)
        candidate = _validated_revision(candidate_path, base, case.base_sha256)
        gold = _validated_revision(gold_path, base, case.base_sha256)
        if case.source_kind == "canonical":
            if source_path != base_path:
                raise ValueError(f"Canonical source must equal base path for {case.case_id}")
            source_text = _canonical_text(base)
            source_revision_number = None
        else:
            source = _validated_revision(source_path, base, case.base_sha256)
            if source.revision_number >= gold.revision_number:
                raise ValueError(f"Source revision must precede gold for {case.case_id}")
            source_text = _revision_text(source)
            source_revision_number = source.revision_number
        gold_text = _revision_text(gold)
        candidate_text = _revision_text(candidate)
        baseline = score(gold_text, source_text)
        result = score(gold_text, candidate_text)
        baseline_errors = cast(dict[str, int], baseline["word_errors"])["errors"]
        candidate_errors = cast(dict[str, int], result["word_errors"])["errors"]
        reports.append(
            {
                "case_id": case.case_id,
                "source_kind": case.source_kind,
                "source_revision_number": source_revision_number,
                "candidate_revision_number": candidate.revision_number,
                "gold_revision_number": gold.revision_number,
                "base_sha256": case.base_sha256,
                "source_sha256": case.source_sha256,
                "candidate_sha256": case.candidate_sha256,
                "gold_sha256": case.gold_sha256,
                "baseline": baseline,
                "candidate": result,
                "word_error_reduction": baseline_errors - candidate_errors,
                "excess_word_errors": max(0, candidate_errors - baseline_errors),
            }
        )
    return {
        "report_version": "ewp-correction-benchmark-v1",
        "manifest_sha256": _sha256(manifest.path),
        "normalization": NORMALIZATION_VERSION,
        "case_count": len(reports),
        "cases": reports,
    }


def _validated_revision(
    path: Path,
    base: CanonicalResult,
    base_sha256: str,
) -> TranscriptRevision:
    revision = load_transcript_revision(path)
    validate_revision_base(revision, base, base_sha256=base_sha256)
    return revision


def _canonical_text(base: CanonicalResult) -> str:
    return " ".join(word.text for segment in base.transcript.segments for word in segment.words)


def _revision_text(revision: TranscriptRevision) -> str:
    return " ".join(token.text for token in revision.transcript.tokens)


def _string(raw: dict[object, object], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Correction benchmark field {field} must be a non-empty string")
    return value


def _relative(raw: dict[object, object], field: str) -> Path:
    path = Path(_string(raw, field))
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError("Correction benchmark paths must be safe relative paths")
    return path


def _sha_field(raw: dict[object, object], field: str) -> str:
    value = _string(raw, field).casefold()
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"Correction benchmark field {field} must be SHA-256")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ValueError(f"Cannot read correction benchmark artifact: {path.name}") from error
    return digest.hexdigest()


def _require_hash(path: Path, expected: str, case_id: str, role: str) -> None:
    if _sha256(path) != expected:
        raise ValueError(f"Correction benchmark {role} SHA-256 mismatch for {case_id}")
