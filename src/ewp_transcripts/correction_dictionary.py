"""Project-scoped correction dictionary proposals from exact manual revisions."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.domain.correction import CorrectionDictionaryTerm
from ewp_transcripts.domain.errors import InvalidCorrectionResponseError
from ewp_transcripts.domain.revision import (
    load_transcript_revision,
    sha256_file,
    validate_revision_base,
)
from ewp_transcripts.revision_audit import build_revision_audit


class CorrectionDictionaryCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    occurrences: int = Field(ge=1)
    case_count: int = Field(ge=1)
    status: Literal["pending", "approved", "rejected"] = "pending"


class CorrectionDictionaryProposal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    proposal_version: Literal["1.0"] = "1.0"
    project_id: str = Field(min_length=1)
    source_language: Literal["pl"] = "pl"
    canonical_directory_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    revision_directory_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    case_count: int = Field(ge=1)
    job_ids: tuple[str, ...] = Field(min_length=1)
    minimum_occurrences: int = Field(ge=1)
    candidates: tuple[CorrectionDictionaryCandidate, ...]


class CorrectionDictionaryEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)


class ProjectCorrectionDictionary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    dictionary_version: Literal["1.0"] = "1.0"
    dictionary_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    project_id: str = Field(min_length=1)
    language: Literal["pl"] = "pl"
    job_ids: tuple[str, ...] = Field(min_length=1)
    proposal_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    entries: tuple[CorrectionDictionaryEntry, ...] = Field(min_length=1)


def propose_correction_dictionary(
    *,
    canonical_directory: Path,
    revision_directory: Path,
    project_id: str,
    minimum_occurrences: int = 2,
) -> CorrectionDictionaryProposal:
    """Aggregate consistent lexical mappings from latest exact manual revisions."""

    bases = {path.name: path for path in canonical_directory.glob("*_results.json")}
    selected: dict[str, tuple[int, Path]] = {}
    for path in revision_directory.glob("*_revision_*.json"):
        if path.name.endswith("_audit.json"):
            continue
        revision = load_transcript_revision(path)
        if revision.provenance.method != "manual" or revision.base_result.filename not in bases:
            continue
        previous = selected.get(revision.job_id)
        if previous is None or revision.revision_number > previous[0]:
            selected[revision.job_id] = (revision.revision_number, path)
    if not selected:
        raise ValueError("No compatible manual revisions found for dictionary proposal")
    mappings: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for job_id, (_number, revision_path) in sorted(selected.items()):
        revision = load_transcript_revision(revision_path)
        assert revision.base_result.filename is not None
        base_path = bases[revision.base_result.filename]
        base = load_canonical_result(base_path)
        validate_revision_base(revision, base, base_sha256=sha256_file(base_path))
        audit = build_revision_audit(
            base, revision, base_path=base_path, revision_path=revision_path
        )
        changes = cast(list[dict[str, object]], audit["changes"])
        for change in changes:
            if change["classification"] not in {"substitution", "merge", "split"}:
                continue
            before, after = change["before"], change["after"]
            if (
                isinstance(before, str)
                and isinstance(after, str)
                and before.casefold() != after.casefold()
            ):
                mappings[before.casefold()].append((before, after, job_id))
    candidates: list[CorrectionDictionaryCandidate] = []
    for observations in mappings.values():
        targets = {after.casefold() for _before, after, _job in observations}
        if len(targets) != 1:
            continue
        if len(observations) < minimum_occurrences:
            continue
        candidates.append(
            CorrectionDictionaryCandidate(
                source=observations[0][0],
                target=observations[0][1],
                occurrences=len(observations),
                case_count=len({job for _before, _after, job in observations}),
            )
        )
    candidates.sort(key=lambda item: (-item.case_count, -item.occurrences, item.source.casefold()))
    return CorrectionDictionaryProposal(
        project_id=project_id,
        canonical_directory_sha256=_directory_hash(bases.values()),
        revision_directory_sha256=_directory_hash(path for _number, path in selected.values()),
        case_count=len(selected),
        job_ids=tuple(sorted(selected)),
        minimum_occurrences=minimum_occurrences,
        candidates=tuple(candidates),
    )


def write_correction_dictionary_proposal(
    proposal: CorrectionDictionaryProposal, output_path: Path
) -> None:
    if output_path.exists():
        raise ValueError(f"Dictionary proposal output already exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    output_path.write_text(proposal.model_dump_json(indent=2) + "\n", encoding="utf-8")


def approve_correction_dictionary(
    *, proposal_path: Path, dictionary_id: str, output_path: Path
) -> ProjectCorrectionDictionary:
    payload = proposal_path.read_bytes()
    proposal = CorrectionDictionaryProposal.model_validate_json(payload)
    if any(candidate.status == "pending" for candidate in proposal.candidates):
        raise ValueError("Dictionary proposal still contains pending candidates")
    approved = tuple(
        CorrectionDictionaryEntry(source=item.source, target=item.target)
        for item in proposal.candidates
        if item.status == "approved"
    )
    dictionary = ProjectCorrectionDictionary(
        dictionary_id=dictionary_id,
        project_id=proposal.project_id,
        job_ids=proposal.job_ids,
        proposal_sha256=hashlib.sha256(payload).hexdigest(),
        entries=approved,
    )
    if output_path.exists():
        raise ValueError(f"Correction dictionary output already exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    output_path.write_text(dictionary.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return dictionary


def load_project_correction_dictionary(path: Path) -> tuple[ProjectCorrectionDictionary, str]:
    try:
        payload = path.read_bytes()
        dictionary = ProjectCorrectionDictionary.model_validate_json(payload)
    except (OSError, UnicodeError, ValueError) as error:
        raise InvalidCorrectionResponseError(
            f"Cannot read valid project correction dictionary: {path}"
        ) from error
    return dictionary, hashlib.sha256(payload).hexdigest()


def select_correction_dictionary_terms(
    dictionary: ProjectCorrectionDictionary, editable_text: str
) -> tuple[CorrectionDictionaryTerm, ...]:
    """Select source-present terms as model context; never rewrite text directly."""

    selected = []
    for entry in dictionary.entries:
        pattern = rf"(?<!\w){re.escape(entry.source)}(?!\w)"
        if re.search(pattern, editable_text, flags=re.IGNORECASE):
            selected.append(CorrectionDictionaryTerm(source=entry.source, target=entry.target))
    return tuple(selected)


def _directory_hash(paths) -> str:  # type: ignore[no-untyped-def]
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(sha256_file(path).encode())
        digest.update(b"\0")
    return digest.hexdigest()
