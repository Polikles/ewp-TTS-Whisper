"""Exact-lineage lexical benchmarks for automated transcript correction."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
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
from ewp_transcripts.quality import score

SourceKind = Literal["canonical", "revision"]
CORRECTION_NORMALIZATION_VERSION = "ewp-correction-lexical-v2"
_ANNOTATION = re.compile(r"\([^()]*\)|\[[^\[\]]*\]")


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


def build_correction_benchmark_bundle(
    *,
    base_directory: Path,
    candidate_directory: Path,
    gold_directory: Path,
    output_directory: Path,
) -> Path:
    """Stage exact private artifacts and write a path-safe canonical-source manifest."""

    candidates = sorted(
        path
        for path in candidate_directory.glob("*_revision_*.json")
        if not path.name.endswith("_audit.json")
    )
    if not candidates:
        raise ValueError("Correction benchmark candidate directory contains no revisions")
    output_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_directory, 0o700)
    artifact_root = output_directory / "artifacts"
    artifact_root.mkdir(mode=0o700, exist_ok=True)
    cases: list[dict[str, str]] = []
    seen: set[str] = set()
    gold_paths = sorted(
        path
        for path in gold_directory.glob("*_revision_*.json")
        if not path.name.endswith("_audit.json")
    )
    for candidate_path in candidates:
        candidate = load_transcript_revision(candidate_path)
        case_id = candidate.job_id
        if case_id in seen:
            raise ValueError(f"Multiple correction candidates for job: {case_id}")
        seen.add(case_id)
        filename = candidate.base_result.filename
        if filename is None:
            raise ValueError(f"Correction candidate lacks base filename: {case_id}")
        base_path = base_directory / filename
        base = load_canonical_result(base_path)
        validate_revision_base(candidate, base, base_sha256=candidate.base_result.sha256)
        compatible_gold: list[tuple[int, Path, TranscriptRevision]] = []
        for gold_path in gold_paths:
            gold = load_transcript_revision(gold_path)
            if gold.job_id != case_id or gold.base_result.sha256 != candidate.base_result.sha256:
                continue
            validate_revision_base(gold, base, base_sha256=candidate.base_result.sha256)
            compatible_gold.append((gold.revision_number, gold_path, gold))
        if not compatible_gold:
            raise ValueError(f"No compatible manual gold revision for job: {case_id}")
        _, gold_path, _ = max(compatible_gold, key=lambda item: item[0])
        staged = {
            "base": _stage(base_path, artifact_root / "base" / base_path.name),
            "candidate": _stage(candidate_path, artifact_root / "candidate" / candidate_path.name),
            "gold": _stage(gold_path, artifact_root / "gold" / gold_path.name),
        }
        cases.append(
            {
                "case_id": case_id,
                "base_path": staged["base"].relative_to(output_directory).as_posix(),
                "base_sha256": _sha256(staged["base"]),
                "source_kind": "canonical",
                "source_path": staged["base"].relative_to(output_directory).as_posix(),
                "source_sha256": _sha256(staged["base"]),
                "candidate_path": staged["candidate"].relative_to(output_directory).as_posix(),
                "candidate_sha256": _sha256(staged["candidate"]),
                "gold_path": staged["gold"].relative_to(output_directory).as_posix(),
                "gold_sha256": _sha256(staged["gold"]),
            }
        )
    manifest_path = output_directory / "manifest.toml"
    lines = [
        'manifest_version = "1.0"',
        f'normalization = "{CORRECTION_NORMALIZATION_VERSION}"',
        "",
    ]
    for case in cases:
        lines.append("[[cases]]")
        lines.extend(f"{key} = {json.dumps(value)}" for key, value in case.items())
        lines.append("")
    manifest_path.write_text("\n".join(lines), encoding="utf-8")
    os.chmod(manifest_path, 0o600)
    return manifest_path


def _stage(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(mode=0o700, exist_ok=True)
    if destination.exists() and destination.read_bytes() != source.read_bytes():
        raise ValueError(f"Correction benchmark staged artifact differs: {destination.name}")
    if not destination.exists():
        shutil.copyfile(source, destination)
    os.chmod(destination, 0o600)
    return destination


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
    if document["normalization"] != CORRECTION_NORMALIZATION_VERSION:
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
        baseline = _correction_score(gold_text, source_text)
        result = _correction_score(gold_text, candidate_text)
        source_to_candidate = _correction_score(source_text, candidate_text)
        baseline_errors = cast(dict[str, int], baseline["word_errors"])["errors"]
        candidate_errors = cast(dict[str, int], result["word_errors"])["errors"]
        word_error_reduction = baseline_errors - candidate_errors
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
                "source_to_candidate": source_to_candidate,
                "word_error_reduction": word_error_reduction,
                "excess_word_errors": max(0, candidate_errors - baseline_errors),
                "lexical_outcome": (
                    "improved"
                    if word_error_reduction > 0
                    else "regressed"
                    if word_error_reduction < 0
                    else "unchanged"
                ),
            }
        )
    return {
        "report_version": "ewp-correction-benchmark-v3",
        "manifest_sha256": _sha256(manifest.path),
        "normalization": CORRECTION_NORMALIZATION_VERSION,
        "case_count": len(reports),
        "aggregate": _aggregate(reports),
        "cases": reports,
    }


def _aggregate(reports: list[dict[str, object]]) -> dict[str, object]:
    """Aggregate the three comparisons without exposing transcript content."""

    comparisons = ("baseline", "source_to_candidate", "candidate")
    totals: dict[str, dict[str, int]] = {
        name: {"errors": 0, "reference_units": 0} for name in comparisons
    }
    for report in reports:
        for name in comparisons:
            metric = cast(dict[str, object], report[name])
            counts = cast(dict[str, int], metric["word_errors"])
            totals[name]["errors"] += counts["errors"]
            totals[name]["reference_units"] += counts["reference_units"]
    aggregate: dict[str, object] = {
        name: {
            "wer": round(total["errors"] / total["reference_units"], 8),
            "word_errors": total["errors"],
            "reference_words": total["reference_units"],
        }
        for name, total in totals.items()
    }
    baseline_errors = totals["baseline"]["errors"]
    candidate_errors = totals["candidate"]["errors"]
    candidate_word_changes = totals["source_to_candidate"]["errors"]
    word_error_reduction = baseline_errors - candidate_errors
    aggregate["lexical_correction"] = {
        "word_error_reduction": word_error_reduction,
        "relative_word_error_reduction": (
            round(word_error_reduction / baseline_errors, 8) if baseline_errors else None
        ),
        "candidate_word_changes": candidate_word_changes,
        "net_correction_efficiency": (
            round(word_error_reduction / candidate_word_changes, 8)
            if candidate_word_changes
            else None
        ),
        "improved_cases": sum(report["lexical_outcome"] == "improved" for report in reports),
        "unchanged_cases": sum(report["lexical_outcome"] == "unchanged" for report in reports),
        "regressed_cases": sum(report["lexical_outcome"] == "regressed" for report in reports),
    }
    return aggregate


def _correction_score(reference_text: str, hypothesis_text: str) -> dict[str, object]:
    metric = score(_without_annotations(reference_text), _without_annotations(hypothesis_text))
    metric["normalization"] = CORRECTION_NORMALIZATION_VERSION
    return metric


def _without_annotations(text: str) -> str:
    """Remove balanced round/square review annotations, including nested annotations."""

    while True:
        stripped = _ANNOTATION.sub(" ", text)
        if stripped == text:
            return stripped
        text = stripped


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
