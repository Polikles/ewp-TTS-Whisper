"""Exact-lineage, human-scored semantic translation benchmarks."""

from __future__ import annotations

import hashlib
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ewp_transcripts.domain.translation import TranscriptTranslation, load_transcript_translation

SemanticStatus = Literal["pending", "faithful", "minor_error", "major_error", "critical_error"]
SemanticCategory = Literal[
    "mistranslation",
    "omission",
    "addition",
    "contradiction",
    "uncertainty",
    "tone_or_register",
]
ConventionStatus = Literal["not_applicable", "pass", "fail"]


class BenchmarkModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class SemanticIssue(BenchmarkModel):
    category: SemanticCategory
    severity: Literal["minor", "major", "critical"]
    note: str | None = None


class TranslationUnitAssessment(BenchmarkModel):
    unit_id: str = Field(pattern=r"^tu_[0-9]{6,}$")
    semantic_status: SemanticStatus = "pending"
    issues: tuple[SemanticIssue, ...] = ()
    convention_status: ConventionStatus = "not_applicable"
    convention_violations: int = Field(default=0, ge=0)
    reviewer_note: str | None = None

    @model_validator(mode="after")
    def validate_assessment(self) -> Self:
        expected = {
            "minor_error": "minor",
            "major_error": "major",
            "critical_error": "critical",
        }.get(self.semantic_status)
        if self.semantic_status in {"pending", "faithful"} and self.issues:
            raise ValueError("pending or faithful units cannot contain semantic issues")
        if expected is not None and not any(issue.severity == expected for issue in self.issues):
            raise ValueError("semantic error status requires an issue of matching severity")
        if self.convention_status == "fail" and self.convention_violations == 0:
            raise ValueError("failed convention assessment requires at least one violation")
        if self.convention_status != "fail" and self.convention_violations:
            raise ValueError("convention violations require failed convention status")
        return self


class TranslationBenchmarkAssessment(BenchmarkModel):
    assessment_version: Literal["1.0"] = "1.0"
    case_id: str = Field(min_length=1)
    candidate_path: str = Field(min_length=1)
    candidate_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    gold_path: str = Field(min_length=1)
    gold_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_language: Literal["pl", "en"]
    target_language: Literal["pl", "en"]
    dictionary_id: str | None = None
    dictionary_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    units: tuple[TranslationUnitAssessment, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dictionary(self) -> Self:
        if (self.dictionary_id is None) != (self.dictionary_sha256 is None):
            raise ValueError("dictionary identity and SHA-256 must be supplied together")
        return self


def prepare_translation_benchmark_assessments(
    *, candidate_directory: Path, gold_directory: Path, output_directory: Path
) -> tuple[Path, ...]:
    """Stage exact artifacts and create reviewer-owned semantic assessment templates."""

    candidates = _translations(candidate_directory)
    golds = _translations(gold_directory)
    if not candidates:
        raise ValueError("Translation benchmark candidate directory contains no translations")
    output_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_directory, 0o700)
    staged_root = output_directory / "artifacts"
    assessments: list[Path] = []
    seen: set[str] = set()
    for candidate_path, candidate in candidates:
        if candidate.provenance.method != "llm":
            raise ValueError(
                f"Translation benchmark candidate must use LLM provenance: {candidate.job_id}"
            )
        case_id = candidate.job_id
        if case_id in seen:
            raise ValueError(f"Multiple translation candidates for job: {case_id}")
        seen.add(case_id)
        compatible = [
            (path, gold)
            for path, gold in golds
            if gold.job_id == case_id
            and gold.provenance.method == "manual"
            and _same_benchmark_contract(candidate, gold)
        ]
        if not compatible:
            raise ValueError(f"No compatible manual translation gold for job: {case_id}")
        gold_path, gold = max(compatible, key=lambda item: item[1].translation_number)
        candidate_staged = _stage(candidate_path, staged_root / "candidate" / candidate_path.name)
        gold_staged = _stage(gold_path, staged_root / "gold" / gold_path.name)
        assessment = TranslationBenchmarkAssessment(
            case_id=case_id,
            candidate_path=candidate_staged.relative_to(output_directory).as_posix(),
            candidate_sha256=_sha256(candidate_staged),
            gold_path=gold_staged.relative_to(output_directory).as_posix(),
            gold_sha256=_sha256(gold_staged),
            source_language=candidate.direction.source_language,
            target_language=candidate.direction.target_language,
            units=tuple(
                TranslationUnitAssessment(unit_id=unit.unit_id) for unit in candidate.units
            ),
        )
        assessment_path = output_directory / f"{case_id}_semantic_assessment.json"
        assessment_path.write_text(assessment.model_dump_json(indent=2) + "\n", encoding="utf-8")
        os.chmod(assessment_path, 0o600)
        assessments.append(assessment_path)
    return tuple(assessments)


def evaluate_translation_benchmark(assessment_paths: tuple[Path, ...]) -> dict[str, object]:
    """Validate completed human assessments and emit a content-free semantic report."""

    if not assessment_paths:
        raise ValueError("Translation benchmark requires assessment files")
    cases: list[dict[str, object]] = []
    directions: set[tuple[str, str]] = set()
    seen: set[str] = set()
    for path in sorted(assessment_paths):
        assessment = TranslationBenchmarkAssessment.model_validate_json(
            path.read_text(encoding="utf-8")
        )
        if assessment.case_id in seen:
            raise ValueError(f"Duplicate translation benchmark case: {assessment.case_id}")
        seen.add(assessment.case_id)
        if any(unit.semantic_status == "pending" for unit in assessment.units):
            raise ValueError(
                f"Translation benchmark assessment is incomplete: {assessment.case_id}"
            )
        root = path.parent
        candidate_path = _safe_artifact(root, assessment.candidate_path)
        gold_path = _safe_artifact(root, assessment.gold_path)
        _require_hash(candidate_path, assessment.candidate_sha256, assessment.case_id, "candidate")
        _require_hash(gold_path, assessment.gold_sha256, assessment.case_id, "gold")
        candidate = load_transcript_translation(candidate_path)
        gold = load_transcript_translation(gold_path)
        if not _same_benchmark_contract(candidate, gold):
            raise ValueError(f"Translation benchmark lineage differs for {assessment.case_id}")
        expected_units = tuple(unit.unit_id for unit in candidate.units)
        assessed_units = tuple(unit.unit_id for unit in assessment.units)
        if assessed_units != expected_units:
            raise ValueError(
                f"Translation benchmark unit coverage differs for {assessment.case_id}"
            )
        direction = (assessment.source_language, assessment.target_language)
        if direction != (candidate.direction.source_language, candidate.direction.target_language):
            raise ValueError(f"Translation benchmark direction differs for {assessment.case_id}")
        directions.add(direction)
        status_counts = Counter(unit.semantic_status for unit in assessment.units)
        category_counts = Counter(
            issue.category for unit in assessment.units for issue in unit.issues
        )
        convention_counts = Counter(unit.convention_status for unit in assessment.units)
        cases.append(
            {
                "case_id": assessment.case_id,
                "direction": f"{direction[0]}->{direction[1]}",
                "candidate_sha256": assessment.candidate_sha256,
                "gold_sha256": assessment.gold_sha256,
                "unit_count": len(assessment.units),
                "semantic_status_counts": dict(sorted(status_counts.items())),
                "semantic_issue_counts": dict(sorted(category_counts.items())),
                "semantic_pass_rate": round(status_counts["faithful"] / len(assessment.units), 8),
                "convention_status_counts": dict(sorted(convention_counts.items())),
                "convention_violations": sum(
                    unit.convention_violations for unit in assessment.units
                ),
                "dictionary": (
                    {"id": assessment.dictionary_id, "sha256": assessment.dictionary_sha256}
                    if assessment.dictionary_id is not None
                    else None
                ),
            }
        )
    if len(directions) != 1:
        raise ValueError("Translation benchmark directions must be reported separately")
    return {
        "report_version": "ewp-translation-semantic-benchmark-v1",
        "evaluation": "human semantic fidelity; no lexical-overlap quality score",
        "direction": cases[0]["direction"],
        "case_count": len(cases),
        "aggregate": _aggregate(cases),
        "cases": cases,
    }


def _aggregate(cases: list[dict[str, object]]) -> dict[str, object]:
    statuses: Counter[str] = Counter()
    issues: Counter[str] = Counter()
    conventions: Counter[str] = Counter()
    violations = 0
    for case in cases:
        statuses.update(cast(dict[str, int], case["semantic_status_counts"]))
        issues.update(cast(dict[str, int], case["semantic_issue_counts"]))
        conventions.update(cast(dict[str, int], case["convention_status_counts"]))
        violations += cast(int, case["convention_violations"])
    total = sum(statuses.values())
    return {
        "unit_count": total,
        "semantic_status_counts": dict(sorted(statuses.items())),
        "semantic_issue_counts": dict(sorted(issues.items())),
        "semantic_pass_rate": round(statuses["faithful"] / total, 8),
        "convention_status_counts": dict(sorted(conventions.items())),
        "convention_violations": violations,
    }


def _translations(directory: Path) -> list[tuple[Path, TranscriptTranslation]]:
    return [
        (path, load_transcript_translation(path))
        for path in sorted(directory.glob("*_translation_*.json"))
        if not path.name.endswith("_audit.json")
    ]


def _same_benchmark_contract(left: TranscriptTranslation, right: TranscriptTranslation) -> bool:
    return (
        left.job_id == right.job_id
        and left.direction == right.direction
        and left.style == right.style
        and left.source == right.source
        and tuple(
            (
                unit.unit_id,
                unit.speaker_id,
                unit.source_token_ids,
                unit.source_text_sha256,
                unit.start_ms,
                unit.end_ms,
            )
            for unit in left.units
        )
        == tuple(
            (
                unit.unit_id,
                unit.speaker_id,
                unit.source_token_ids,
                unit.source_text_sha256,
                unit.start_ms,
                unit.end_ms,
            )
            for unit in right.units
        )
    )


def _stage(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.exists() and destination.read_bytes() != source.read_bytes():
        raise ValueError(f"Translation benchmark staged artifact differs: {destination.name}")
    if not destination.exists():
        shutil.copyfile(source, destination)
    os.chmod(destination, 0o600)
    return destination


def _safe_artifact(root: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError("Translation benchmark paths must be safe relative paths")
    return root / relative


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ValueError(f"Cannot read translation benchmark artifact: {path.name}") from error


def _require_hash(path: Path, expected: str, case_id: str, role: str) -> None:
    if _sha256(path) != expected:
        raise ValueError(f"Translation benchmark {role} SHA-256 mismatch for {case_id}")
