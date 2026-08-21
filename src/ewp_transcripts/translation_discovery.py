"""Deterministic discovery and exact source resolution for translation batches."""

from __future__ import annotations

import re
from pathlib import Path

from ewp_transcripts.discovery import natural_path_key, normalize_input_path
from ewp_transcripts.domain.canonical import CanonicalResult, load_canonical_result
from ewp_transcripts.domain.errors import (
    InputNotFoundError,
    InvalidRevisionError,
    InvalidTranslationError,
    SymlinkInputError,
    UnsupportedInputError,
)
from ewp_transcripts.domain.revision import (
    load_transcript_revision,
    sha256_file,
    validate_revision_base,
)
from ewp_transcripts.domain.translation_review import TranslationReview

_TRANSLATION_REVIEW_NAME = re.compile(
    r"^.+_(?:pl|en)\.translation\.review(?:_v[0-9]{3,})?\.txt$"
)


def discover_translation_reviews(
    input_path: str | Path, *, recursive: bool = False
) -> tuple[Path, ...]:
    path = normalize_input_path(input_path)
    if path.is_symlink():
        raise SymlinkInputError(f"Translation review input must not be a symbolic link: {path}")
    if not path.exists():
        raise InputNotFoundError(f"Translation review input does not exist: {path}")
    if path.is_file():
        return (path,)
    if not path.is_dir():
        raise UnsupportedInputError(
            f"Translation review input must be a regular file or directory: {path}"
        )
    entries = path.rglob("*") if recursive else path.iterdir()
    candidates = [
        candidate.absolute()
        for candidate in entries
        if candidate.is_file()
        and not candidate.is_symlink()
        and _TRANSLATION_REVIEW_NAME.fullmatch(candidate.name) is not None
    ]
    candidates.sort(key=lambda candidate: (natural_path_key(candidate), candidate.as_posix()))
    return tuple(candidates)


def latest_compatible_revision_path(
    directory: Path, *, result_path: Path, result: CanonicalResult
) -> Path:
    result_suffix = "" if result.result_version == 1 else f"_v{result.result_version:03d}"
    pattern = re.compile(
        rf"^{re.escape(result.job_id + result_suffix)}_revision_(?P<number>[0-9]{{3,}})\.json$"
    )
    candidates = sorted(
        (
            (int(match.group("number")), path)
            for path in directory.iterdir()
            if path.is_file() and (match := pattern.fullmatch(path.name)) is not None
        ),
        reverse=True,
    )
    result_hash = sha256_file(result_path)
    for _, candidate_path in candidates:
        candidate = load_transcript_revision(candidate_path)
        try:
            validate_revision_base(candidate, result, base_sha256=result_hash)
        except InvalidRevisionError:
            continue
        return candidate_path
    raise InvalidRevisionError(f"No compatible transcript revision was found for {result.job_id}")


def resolve_translation_review_sources(
    review: TranslationReview,
    *,
    results_directory: Path,
    revisions_directory: Path | None = None,
) -> tuple[Path, Path | None]:
    canonical = review.header.source.canonical_result
    result_path = results_directory / canonical.filename
    if not result_path.is_file() or sha256_file(result_path) != canonical.sha256:
        raise InvalidTranslationError(
            "Cannot locate the translation review's exact canonical result"
        )
    result = load_canonical_result(result_path)
    if result.job_id != canonical.job_id or result.result_version != canonical.result_version:
        raise InvalidTranslationError("Translation review canonical identity does not match")
    revision_source = review.header.source.transcript_revision
    if revision_source is None:
        return result_path, None
    directory = revisions_directory or results_directory
    revision_path = directory / revision_source.filename
    if not revision_path.is_file() or sha256_file(revision_path) != revision_source.sha256:
        raise InvalidTranslationError(
            "Cannot locate the translation review's exact transcript revision"
        )
    revision = load_transcript_revision(revision_path)
    if (
        revision.revision_id != revision_source.revision_id
        or revision.revision_number != revision_source.revision_number
        or revision.provenance.method != revision_source.method
    ):
        raise InvalidTranslationError("Translation review revision identity does not match")
    return result_path, revision_path
