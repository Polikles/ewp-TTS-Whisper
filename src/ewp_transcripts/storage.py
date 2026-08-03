"""Pure output-directory and filename planning helpers."""

from __future__ import annotations

from pathlib import Path

from ewp_transcripts.config import OutputsConfig
from ewp_transcripts.domain import DiscoveryResult, PlannedOutputPaths
from ewp_transcripts.domain.errors import UnsafeOutputNameError


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
