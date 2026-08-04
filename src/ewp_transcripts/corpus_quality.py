"""Manifest-driven lexical corpus evaluation and review reports."""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from ewp_transcripts.quality import (
    NORMALIZATION_VERSION,
    read_hypothesis,
    score,
    word_error_diff,
)

HypothesisFormat = Literal["auto", "text", "whisperx-json", "canonical-json"]


@dataclass(frozen=True, slots=True)
class CorpusCase:
    case_id: str
    language: str
    reference_path: Path
    reference_sha256: str
    hypothesis_path: Path
    hypothesis_format: HypothesisFormat


@dataclass(frozen=True, slots=True)
class CorpusManifest:
    path: Path
    cases: tuple[CorpusCase, ...]


def load_corpus_manifest(path: Path) -> CorpusManifest:
    """Load the strict lexical-evaluation subset of an external corpus manifest."""

    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ValueError("Cannot read corpus manifest") from error
    allowed_root = {"manifest_version", "normalization", "cases"}
    if set(document) - allowed_root:
        raise ValueError("Corpus manifest contains unknown root fields")
    if document.get("manifest_version") != "1.0":
        raise ValueError("Unsupported corpus manifest version")
    if document.get("normalization") != NORMALIZATION_VERSION:
        raise ValueError("Corpus manifest normalization does not match the scorer")
    raw_cases = document.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("Corpus manifest must contain at least one case")
    cases: list[CorpusCase] = []
    seen_ids: set[str] = set()
    allowed_case = {
        "case_id",
        "language",
        "reference_path",
        "reference_sha256",
        "hypothesis_path",
        "hypothesis_format",
    }
    for raw in raw_cases:
        if not isinstance(raw, dict) or set(raw) != allowed_case:
            raise ValueError("Each corpus case must contain exactly the documented fields")
        case_id = _required_string(raw, "case_id")
        if case_id in seen_ids:
            raise ValueError(f"Duplicate corpus case ID: {case_id}")
        seen_ids.add(case_id)
        reference_path = _safe_relative(_required_string(raw, "reference_path"))
        hypothesis_path = _safe_relative(_required_string(raw, "hypothesis_path"))
        reference_sha256 = _required_string(raw, "reference_sha256").casefold()
        if len(reference_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in reference_sha256
        ):
            raise ValueError(f"Invalid reference SHA-256 for case {case_id}")
        hypothesis_format = _required_string(raw, "hypothesis_format")
        if hypothesis_format not in {"auto", "text", "whisperx-json", "canonical-json"}:
            raise ValueError(f"Invalid hypothesis format for case {case_id}")
        cases.append(
            CorpusCase(
                case_id=case_id,
                language=_required_string(raw, "language"),
                reference_path=reference_path,
                reference_sha256=reference_sha256,
                hypothesis_path=hypothesis_path,
                hypothesis_format=cast(HypothesisFormat, hypothesis_format),
            )
        )
    return CorpusManifest(path=path, cases=tuple(cases))


def evaluate_corpus(
    manifest: CorpusManifest,
    *,
    hypothesis_root: Path,
) -> tuple[dict[str, object], str]:
    """Score every case and return machine and error-only human reports."""

    case_reports: list[dict[str, object]] = []
    diff_sections: list[str] = []
    total_word_errors = _zero_counts()
    total_character_errors = _zero_counts()
    for case in manifest.cases:
        reference_path = manifest.path.parent / case.reference_path
        hypothesis_path = hypothesis_root / case.hypothesis_path
        actual_reference_hash = _sha256(reference_path)
        if actual_reference_hash != case.reference_sha256:
            raise ValueError(f"Reference SHA-256 mismatch for case {case.case_id}")
        reference_text = reference_path.read_text(encoding="utf-8")
        hypothesis_text, selected_format = read_hypothesis(hypothesis_path, case.hypothesis_format)
        metrics = score(reference_text, hypothesis_text)
        word_counts = cast(dict[str, int], metrics["word_errors"])
        character_counts = cast(dict[str, int], metrics["character_errors"])
        _accumulate(total_word_errors, word_counts)
        _accumulate(total_character_errors, character_counts)
        case_reports.append(
            {
                "case_id": case.case_id,
                "language": case.language,
                "reference_path": case.reference_path.as_posix(),
                "reference_sha256": actual_reference_hash,
                "hypothesis_path": case.hypothesis_path.as_posix(),
                "hypothesis_sha256": _sha256(hypothesis_path),
                "hypothesis_format": selected_format,
                **metrics,
            }
        )
        operations = word_error_diff(reference_text, hypothesis_text)
        diff_sections.append(f"## {case.case_id}")
        diff_sections.extend(operations or ("No lexical word errors.",))
        diff_sections.append("")
    macro_wer = sum(cast(float, report["wer"]) for report in case_reports) / len(case_reports)
    macro_cer = sum(cast(float, report["cer"]) for report in case_reports) / len(case_reports)
    report: dict[str, object] = {
        "report_version": "ewp-corpus-quality-v1",
        "manifest_file": manifest.path.name,
        "manifest_sha256": _sha256(manifest.path),
        "normalization": NORMALIZATION_VERSION,
        "case_count": len(case_reports),
        "cases": case_reports,
        "aggregate": {
            "macro_average": {
                "wer": round(macro_wer, 8),
                "cer": round(macro_cer, 8),
            },
            "micro_average": {
                "wer": _rate(total_word_errors),
                "cer": _rate(total_character_errors),
                "word_errors": total_word_errors,
                "character_errors": total_character_errors,
            },
        },
    }
    return report, "\n".join(diff_sections).rstrip() + "\n"


def _required_string(document: dict[object, object], field: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Corpus field {field} must be a non-empty string")
    return value


def _safe_relative(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError("Corpus paths must be safe relative paths")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ValueError(f"Cannot read corpus file: {path.name}") from error
    return digest.hexdigest()


def _zero_counts() -> dict[str, int]:
    return {
        "substitutions": 0,
        "deletions": 0,
        "insertions": 0,
        "reference_units": 0,
        "errors": 0,
    }


def _accumulate(total: dict[str, int], counts: dict[str, int]) -> None:
    for field in total:
        total[field] += counts[field]


def _rate(counts: dict[str, int]) -> float:
    reference_units = counts["reference_units"]
    if not reference_units:
        raise ValueError("Corpus contains no normalized reference units")
    return round(counts["errors"] / reference_units, 8)
