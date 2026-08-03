"""Pure output-directory and filename planning helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ewp_transcripts.config import OutputsConfig
from ewp_transcripts.domain import (
    ApplicationWarning,
    DiscoveryResult,
    EpisodeInspection,
    ExistingResult,
    JobOutputPlan,
    PlannedOutputPaths,
    WarningCode,
)
from ewp_transcripts.domain.enums import PlanDecision
from ewp_transcripts.domain.errors import InvalidExistingResultError, UnsafeOutputNameError

_FINAL_RESULT_NAME = re.compile(r"^.+_results(?:_v[0-9]{3,})?\.json$")


def resolve_output_directory(
    discovery: DiscoveryResult,
    *,
    config: OutputsConfig,
    explicit_directory: Path | None = None,
    cwd: Path | None = None,
) -> Path:
    """Resolve the destination without creating or modifying it."""

    if explicit_directory is not None:
        expanded = explicit_directory.expanduser()
        if expanded.is_absolute():
            return expanded
        return ((Path.cwd() if cwd is None else cwd) / expanded).absolute()
    if discovery.input_path.is_file():
        return discovery.input_path.parent
    return discovery.input_path / config.batch_output_directory_name


def _safe_job_id(job_id: str) -> str:
    if not job_id or job_id in {".", ".."} or Path(job_id).name != job_id or "\x00" in job_id:
        raise UnsafeOutputNameError(f"Job ID is not safe for output filenames: {job_id!r}")
    return job_id


def _version_suffix(version: int) -> str:
    if version < 1:
        raise ValueError("result version must be positive")
    return "" if version == 1 else f"_v{version:03d}"


def plan_output_paths(
    output_directory: Path,
    *,
    job_id: str,
    version: int,
    config: OutputsConfig,
) -> PlannedOutputPaths:
    """Plan one coordinated role-first output set without touching the filesystem."""

    safe_job_id = _safe_job_id(job_id)
    suffix = _version_suffix(version)
    results_stem = f"{safe_job_id}_results{suffix}"

    def optional(enabled: bool, role: str, extension: str) -> Path | None:
        return output_directory / f"{safe_job_id}_{role}{suffix}.{extension}" if enabled else None

    return PlannedOutputPaths(
        output_directory=output_directory,
        result_version=version,
        results=output_directory / f"{results_stem}.json",
        partial_results=output_directory / f"{results_stem}.partial.json",
        failed_results=output_directory / f"{results_stem}.failed.json",
        transcript=optional(config.generate_txt, "transcript", "txt"),
        subtitles_srt=optional(config.generate_srt, "subtitles", "srt"),
        subtitles_vtt=optional(config.generate_vtt, "subtitles", "vtt"),
        segments=optional(config.generate_segments_json, "segments", "json"),
    )


def _required(data: dict[str, Any], key: str, expected: type) -> Any:
    value = data.get(key)
    if not isinstance(value, expected) or isinstance(value, bool):
        raise InvalidExistingResultError(f"Completed result has invalid {key!r}")
    return value


def read_existing_result(path: Path) -> ExistingResult:
    """Read only identity/version metadata from one completed canonical result."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise InvalidExistingResultError(f"Cannot read completed result: {path}") from error
    if not isinstance(data, dict) or data.get("status") != "completed":
        raise InvalidExistingResultError(f"Result is not a completed object: {path}")
    episode = data.get("episode")
    if not isinstance(episode, dict):
        raise InvalidExistingResultError(f"Completed result has invalid 'episode': {path}")
    try:
        return ExistingResult(
            path=path,
            job_id=_required(data, "job_id", str),
            episode_signature_sha256=_required(episode, "episode_signature_sha256", str),
            result_version=_required(data, "result_version", int),
        )
    except (ValueError, InvalidExistingResultError) as error:
        if isinstance(error, InvalidExistingResultError):
            raise
        raise InvalidExistingResultError(f"Invalid completed result metadata: {path}") from error


def find_existing_results(output_directory: Path) -> tuple[ExistingResult, ...]:
    """Index final result files deterministically without reading partial/failed states."""

    if not output_directory.exists():
        return ()
    if not output_directory.is_dir():
        raise InvalidExistingResultError(
            f"Output destination is not a directory: {output_directory}"
        )
    paths = sorted(
        (
            path
            for path in output_directory.iterdir()
            if path.is_file() and _FINAL_RESULT_NAME.fullmatch(path.name)
        ),
        key=lambda path: path.name.casefold(),
    )
    return tuple(read_existing_result(path) for path in paths)


def _output_files(paths: PlannedOutputPaths) -> tuple[Path, ...]:
    return tuple(
        path
        for path in (
            paths.results,
            paths.partial_results,
            paths.failed_results,
            paths.transcript,
            paths.subtitles_srt,
            paths.subtitles_vtt,
            paths.segments,
        )
        if path is not None
    )


def _available_output_paths(
    output_directory: Path,
    *,
    job_id: str,
    first_version: int,
    config: OutputsConfig,
) -> PlannedOutputPaths:
    version = first_version
    while True:
        paths = plan_output_paths(
            output_directory,
            job_id=job_id,
            version=version,
            config=config,
        )
        if not any(path.exists() for path in _output_files(paths)):
            return paths
        version += 1


def plan_job_outputs(
    inspection: EpisodeInspection,
    *,
    output_directory: Path,
    existing_results: tuple[ExistingResult, ...],
    force: bool,
    config: OutputsConfig,
) -> JobOutputPlan:
    """Decide skip/process and allocate the first currently available output set."""

    matching_signature = tuple(
        result
        for result in existing_results
        if result.episode_signature_sha256 == inspection.episode_signature_sha256
    )
    if matching_signature and not force:
        existing = max(matching_signature, key=lambda item: item.result_version)
        return JobOutputPlan(
            job_id=inspection.job_id,
            episode_signature_sha256=inspection.episode_signature_sha256,
            decision=PlanDecision.SKIP,
            existing_result=existing,
            warnings=(
                ApplicationWarning(
                    code=WarningCode.EXISTING_RESULT_SKIPPED,
                    message="A completed result with the same episode signature exists.",
                    context={"existing_result": str(existing.path)},
                ),
            ),
        )

    same_job = tuple(result for result in existing_results if result.job_id == inspection.job_id)
    first_version = 1
    warnings: tuple[ApplicationWarning, ...] = ()
    if matching_signature and force:
        first_version = max(2, max(item.result_version for item in matching_signature) + 1)
    elif same_job:
        first_version = max(item.result_version for item in same_job) + 1
        warnings = (
            ApplicationWarning(
                code=WarningCode.SOURCE_NAME_COLLISION,
                message="The job ID exists with a different episode signature.",
                context={"existing_versions": sorted(item.result_version for item in same_job)},
            ),
        )

    outputs = _available_output_paths(
        output_directory,
        job_id=inspection.job_id,
        first_version=first_version,
        config=config,
    )
    return JobOutputPlan(
        job_id=inspection.job_id,
        episode_signature_sha256=inspection.episode_signature_sha256,
        decision=PlanDecision.PROCESS,
        outputs=outputs,
        warnings=warnings,
    )
