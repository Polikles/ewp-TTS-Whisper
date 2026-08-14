"""Terminal adapter for EWP-transcripts."""

import json
import sys
from contextlib import nullcontext, redirect_stdout
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from ewp_transcripts.application import (
    BatchReviewPreparationOutcome,
    BatchRevisionOutcome,
    BatchTranscriptionOutcome,
    ExportFormat,
    TranscriptionOutcome,
    application_version,
    apply_review_file,
    audit_revision_file,
    clean_all_workdirs,
    doctor,
    dry_run,
    export_result,
    inspect_input,
    prepare_review_batch,
    prepare_review_file,
    preview_review_file,
    process_review_batch,
    transcribe_batch,
    transcribe_one,
)
from ewp_transcripts.config import load_config
from ewp_transcripts.discovery import normalize_input_path
from ewp_transcripts.domain import JobOutputPlan, TranscriptRevision
from ewp_transcripts.domain.enums import ChannelMode, LanguageMode, PlanDecision
from ewp_transcripts.domain.errors import (
    ApplicationError,
    InvalidCanonicalResultError,
    InvalidConfigurationError,
    MissingCapabilityError,
    OutputLockUnavailableError,
    OutputReservationError,
)
from ewp_transcripts.revision_editor import open_review_in_editor, require_review_change

app = typer.Typer(
    name="transcriber",
    help=(
        "Local-first transcription for edited podcast and training recordings. "
        "Run 'transcriber COMMAND --help' for command-specific options."
    ),
    no_args_is_help=True,
)
revise_app = typer.Typer(
    name="revise",
    help="Prepare, validate, and publish transcript corrections without source audio.",
    no_args_is_help=True,
)
app.add_typer(revise_app, name="revise")


class RequestedChannelMode(StrEnum):
    """Channel modes users may explicitly request."""

    AUTO = "auto"
    MONO = "mono"
    DUAL_MONO = "dual-mono"
    SPLIT_SPEAKERS = "split-speakers"
    MIXED_STEREO = "mixed-stereo"


class RequestedSpeakerLabels(StrEnum):
    ON_CHANGE = "on-change"
    ALWAYS = "always"
    NEVER = "never"


class RequestedSubtitlePreset(StrEnum):
    YOUTUBE = "youtube"


class RequestedPreset(StrEnum):
    ACCURATE = "accurate"


class RequestedLanguage(StrEnum):
    POLISH = "pl"
    ENGLISH = "en"
    AUTO = "auto"


class RequestedTranscribeFormat(StrEnum):
    TXT = "txt"
    SRT = "srt"
    VTT = "vtt"


class CleanTarget(StrEnum):
    ALL_WORKDIRS = "all-workdirs"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(application_version())
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the application version and exit.",
        ),
    ] = None,
) -> None:
    """Run EWP-transcripts commands."""


def _review_batch_json(outcome: BatchReviewPreparationOutcome) -> str:
    return json.dumps(
        {
            "output_directory": str(outcome.output_directory),
            "prepared": outcome.prepared,
            "failed": outcome.failed,
            "stopped_early": outcome.stopped_early,
            "jobs": [
                {
                    "result_path": str(job.result_path),
                    "status": job.status,
                    "review_path": str(job.review_path) if job.review_path else None,
                    "failure_code": job.failure_code,
                    "failure_message": job.failure_message,
                }
                for job in outcome.jobs
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


@revise_app.command("prepare")
def revise_prepare_command(
    input_path: Annotated[
        Path,
        typer.Argument(
            help="Completed canonical result or directory containing results.",
            metavar="INPUT",
        ),
    ],
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write EWP-REVIEW files to this directory."),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Include completed results in subdirectories."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the batch outcome as JSON."),
    ] = False,
) -> None:
    """Create editable EWP-REVIEW files without loading audio or ML models."""

    try:
        config = load_config(explicit_path=config_path)
        outcome = prepare_review_batch(
            input_path,
            config=config,
            output_directory=_optional_user_path(output_directory),
            recursive=recursive,
            anchor_target_words=config.revision.anchor_target_words,
        )
    except ApplicationError as error:
        _expected_error(error)

    if json_output:
        typer.echo(_review_batch_json(outcome))
    else:
        typer.echo(f"Output directory: {outcome.output_directory}")
        for job in outcome.jobs:
            typer.echo(f"{job.status.upper()} {job.result_path}")
            if job.review_path is not None:
                typer.echo(f"  REVIEW {job.review_path}")
            if job.failure_code is not None:
                typer.echo(f"  ERROR {job.failure_code}: {job.failure_message}")
        typer.echo(
            f"SUMMARY prepared={outcome.prepared} failed={outcome.failed} "
            f"stopped_early={str(outcome.stopped_early).lower()}"
        )
    if outcome.failed:
        raise typer.Exit(code=5)


def _revision_json(
    revision: TranscriptRevision,
    *,
    revision_path: Path | None = None,
) -> str:
    payload = revision.model_dump(mode="json")
    payload["revision_path"] = str(revision_path) if revision_path else None
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _print_revision_preview(revision: TranscriptRevision) -> None:
    typer.echo(f"PREVIEW {revision.job_id}")
    typer.echo(
        f"SUMMARY source_tokens={revision.statistics.source_tokens} "
        f"revision_tokens={revision.statistics.revision_tokens} "
        f"warnings={len(revision.warnings)}"
    )


def _revision_batch_json(outcome: BatchRevisionOutcome) -> str:
    return json.dumps(
        {
            "previewed": outcome.previewed,
            "applied": outcome.applied,
            "failed": outcome.failed,
            "stopped_early": outcome.stopped_early,
            "jobs": [
                {
                    "review_path": str(job.review_path),
                    "status": job.status,
                    "revision_path": str(job.revision_path) if job.revision_path else None,
                    "failure_code": job.failure_code,
                    "failure_message": job.failure_message,
                }
                for job in outcome.jobs
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def _print_revision_batch(outcome: BatchRevisionOutcome) -> None:
    for job in outcome.jobs:
        typer.echo(f"{job.status.upper()} {job.review_path}")
        if job.revision_path is not None:
            typer.echo(f"  REVISION {job.revision_path}")
        if job.failure_code is not None:
            typer.echo(f"  ERROR {job.failure_code}: {job.failure_message}")
    typer.echo(
        f"SUMMARY previewed={outcome.previewed} applied={outcome.applied} "
        f"failed={outcome.failed} stopped_early={str(outcome.stopped_early).lower()}"
    )


@revise_app.command("preview")
def revise_preview_command(
    review_path: Annotated[
        Path,
        typer.Argument(help="EWP-REVIEW file to validate and align.", metavar="REVIEW"),
    ],
    results_directory: Annotated[
        Path | None,
        typer.Option("--results-dir", help="Directory containing the exact base result."),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Include review files in subdirectories."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the unpublished revision as JSON."),
    ] = False,
) -> None:
    """Validate and align a review without writing a revision."""

    try:
        config = load_config(explicit_path=config_path)
        normalized_review = normalize_input_path(review_path)
        if normalized_review.is_dir():
            batch = process_review_batch(
                normalized_review,
                config=config,
                results_directory=_optional_user_path(results_directory),
                recursive=recursive,
                apply=False,
            )
        else:
            outcome = preview_review_file(
                normalized_review,
                results_directory=_optional_user_path(results_directory),
                long_gap_warning_ms=config.revision.long_gap_warning_ms,
            )
    except ApplicationError as error:
        _expected_error(error)
    if normalized_review.is_dir():
        if json_output:
            typer.echo(_revision_batch_json(batch))
        else:
            _print_revision_batch(batch)
        if batch.failed:
            raise typer.Exit(code=5)
    elif json_output:
        typer.echo(_revision_json(outcome.revision))
    else:
        _print_revision_preview(outcome.revision)


@revise_app.command("apply")
def revise_apply_command(
    review_path: Annotated[
        Path,
        typer.Argument(help="EWP-REVIEW file to validate and apply.", metavar="REVIEW"),
    ],
    results_directory: Annotated[
        Path | None,
        typer.Option("--results-dir", help="Directory containing the exact base result."),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write the immutable revision to this directory."),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Include review files in subdirectories."),
    ] = False,
    no_apply: Annotated[
        bool,
        typer.Option("--no-apply", help="Run the complete preview path without writing."),
    ] = False,
    audit: Annotated[
        bool,
        typer.Option("--audit", help="Publish detailed diagnostics after a successful apply."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the revision outcome as JSON."),
    ] = False,
) -> None:
    """Validate a review and publish an immutable full-snapshot revision."""

    try:
        config = load_config(explicit_path=config_path)
        normalized_review = normalize_input_path(review_path)
        if normalized_review.is_dir():
            batch = process_review_batch(
                normalized_review,
                config=config,
                results_directory=_optional_user_path(results_directory),
                output_directory=_optional_user_path(output_directory),
                recursive=recursive,
                apply=not no_apply,
            )
        elif no_apply:
            preview = preview_review_file(
                normalized_review,
                results_directory=_optional_user_path(results_directory),
                long_gap_warning_ms=config.revision.long_gap_warning_ms,
            )
            revision = preview.revision
            revision_path = None
        else:
            applied = apply_review_file(
                normalized_review,
                config=config,
                results_directory=_optional_user_path(results_directory),
                output_directory=_optional_user_path(output_directory),
            )
            revision = applied.revision
            revision_path = applied.revision_path
    except ApplicationError as error:
        _expected_error(error)
    audit_path = None
    if (
        not normalized_review.is_dir()
        and (audit or config.revision.generate_audit)
        and revision_path is not None
    ):
        audit_path = audit_revision_file(
            revision_path,
            config=config,
            results_directory=_optional_user_path(results_directory),
            output_directory=_optional_user_path(output_directory),
        ).audit_path
    if normalized_review.is_dir():
        if (audit or config.revision.generate_audit) and not no_apply:
            for job in batch.jobs:
                if job.revision_path is not None:
                    audit_revision_file(
                        job.revision_path,
                        config=config,
                        results_directory=_optional_user_path(results_directory),
                        output_directory=_optional_user_path(output_directory),
                    )
        if json_output:
            typer.echo(_revision_batch_json(batch))
        else:
            _print_revision_batch(batch)
        if batch.failed:
            raise typer.Exit(code=5)
    elif json_output:
        typer.echo(_revision_json(revision, revision_path=revision_path))
    elif revision_path is None:
        _print_revision_preview(revision)
    else:
        typer.echo(f"APPLIED {revision.job_id}")
        typer.echo(f"  REVISION {revision_path}")
        if audit_path is not None:
            typer.echo(f"  AUDIT {audit_path}")
        typer.echo(
            f"SUMMARY revision_number={revision.revision_number} "
            f"revision_tokens={revision.statistics.revision_tokens} "
            f"warnings={len(revision.warnings)}"
        )


@revise_app.command("audit")
def revise_audit_command(
    revision_path: Annotated[
        Path,
        typer.Argument(help="Immutable transcript revision JSON.", metavar="REVISION"),
    ],
    results_directory: Annotated[
        Path | None,
        typer.Option("--results-dir", help="Directory containing the exact base result."),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write the audit JSON to this directory."),
    ] = None,
    no_write: Annotated[
        bool,
        typer.Option("--no-write", help="Reconstruct and display without publishing an audit."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the reconstructed audit to stdout as JSON."),
    ] = False,
) -> None:
    """Reconstruct detailed diagnostics from a base result and full revision."""

    try:
        config = load_config(explicit_path=config_path)
        outcome = audit_revision_file(
            revision_path,
            config=config,
            results_directory=_optional_user_path(results_directory),
            output_directory=_optional_user_path(output_directory),
            publish=not no_write,
        )
    except ApplicationError as error:
        _expected_error(error)
    if json_output:
        typer.echo(json.dumps(outcome.audit, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"AUDIT {outcome.revision_path}")
        if outcome.audit_path is not None:
            typer.echo(f"  WROTE {outcome.audit_path}")
        changes = outcome.audit.get("changes")
        change_count = len(changes) if isinstance(changes, list) else 0
        typer.echo(f"SUMMARY changes={change_count} written={int(outcome.audit_path is not None)}")


@revise_app.command("edit")
def revise_edit_command(
    results_json: Annotated[
        Path,
        typer.Argument(help="Completed canonical result to review.", metavar="RESULTS_JSON"),
    ],
    review_output_directory: Annotated[
        Path | None,
        typer.Option(
            "--review-output-dir",
            help="Write the editable EWP-REVIEW file to this directory.",
        ),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write the immutable revision to this directory."),
    ] = None,
    no_apply: Annotated[
        bool,
        typer.Option(
            "--no-apply",
            help="Keep editor changes without automatically creating a revision.",
        ),
    ] = False,
    audit: Annotated[
        bool,
        typer.Option("--audit", help="Publish detailed diagnostics after automatic apply."),
    ] = False,
    editor: Annotated[
        str | None,
        typer.Option(
            "--editor",
            help="Installed editor command, for example 'nano' or 'code --wait'.",
        ),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
) -> None:
    """Edit a prepared review; successful editor close applies it unless --no-apply."""

    try:
        normalized_result = normalize_input_path(results_json)
        config = load_config(
            explicit_path=config_path,
            cli_overrides=({"revision": {"editor": editor}} if editor is not None else None),
        )
        review_directory = _optional_user_path(review_output_directory) or (
            normalized_result.parent / "review-ewp-transcripts"
        )
        prepared = prepare_review_file(
            normalized_result,
            output_directory=review_directory,
            anchor_target_words=config.revision.anchor_target_words,
            lock_timeout_seconds=config.runtime.lock_timeout_seconds,
        )
        original_review = prepared.path.read_bytes()
        open_review_in_editor(prepared.path, configured=config.revision.editor)
        require_review_change(prepared.path, original_content=original_review)
        if no_apply:
            typer.echo(f"EDITED {prepared.path}")
            typer.echo("SUMMARY applied=0")
            return
        applied = apply_review_file(
            prepared.path,
            config=config,
            results_directory=normalized_result.parent,
            output_directory=_optional_user_path(output_directory),
        )
        audit_path = None
        if audit or config.revision.generate_audit:
            audit_path = audit_revision_file(
                applied.revision_path,
                config=config,
                results_directory=normalized_result.parent,
                output_directory=_optional_user_path(output_directory),
            ).audit_path
    except ApplicationError as error:
        _expected_error(error)
    typer.echo(f"EDITED {prepared.path}")
    typer.echo(f"APPLIED {applied.revision_path}")
    if audit_path is not None:
        typer.echo(f"AUDIT {audit_path}")
    typer.echo(f"SUMMARY applied=1 revision_number={applied.revision.revision_number}")


@app.command("doctor")
def doctor_command(
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the diagnostic result as JSON."),
    ] = False,
) -> None:
    """Check the local environment without loading transcription models."""

    try:
        config = load_config(explicit_path=config_path)
        result = doctor(config=config)
    except ApplicationError as error:
        _expected_error(error)
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
    else:
        for check in result.checks:
            typer.echo(f"{check.code}: {check.status.value.upper()} — {check.message}")

    if not result.ready:
        raise typer.Exit(code=3)


def _speaker_count(value: str | None) -> str | int | None:
    if value is None or value == "auto":
        return value
    try:
        parsed = int(value)
    except ValueError as error:
        raise typer.BadParameter("must be 'auto' or a positive integer") from error
    if parsed < 1:
        raise typer.BadParameter("must be 'auto' or a positive integer")
    return parsed


def _speaker_mapping(values: list[str] | None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for value in values or []:
        source, separator, label = value.partition("=")
        source = source.strip()
        label = label.strip()
        if not separator or not source or not label:
            raise typer.BadParameter("speaker maps must use SOURCE=NAME")
        if source in mapping:
            raise typer.BadParameter(f"speaker map source repeated: {source}")
        mapping[source] = label
    return mapping


def _inspection_overrides(
    *,
    recursive: bool | None,
    language: RequestedLanguage | None,
    channel_mode: RequestedChannelMode | None,
    speaker_count: str | int | None,
) -> dict[str, object]:
    overrides: dict[str, object] = {}
    if language is not None:
        overrides["general"] = {"language": LanguageMode(language.value)}
    if recursive is not None:
        overrides["input"] = {"recursive": recursive}
    if channel_mode is not None:
        overrides["channels"] = {"mode": ChannelMode(channel_mode.value)}
    if speaker_count is not None:
        overrides["diarization"] = {"speaker_count": speaker_count}
    return overrides


def _transcribe_overrides(
    *,
    recursive: bool,
    language: RequestedLanguage | None,
    channel_mode: RequestedChannelMode | None,
    speaker_count: str | int | None,
    preset: RequestedPreset,
    formats: list[RequestedTranscribeFormat] | None,
    segments: bool,
    keep_temp: bool,
    non_interactive: bool,
) -> dict[str, object]:
    overrides = _inspection_overrides(
        recursive=recursive,
        language=language,
        channel_mode=channel_mode,
        speaker_count=speaker_count,
    )
    general: dict[str, object] = {"preset": preset.value}
    if language is not None:
        general["language"] = LanguageMode(language.value)
    if non_interactive:
        general["interactive"] = False
    overrides["general"] = general
    if formats is not None:
        selected = {format_.value for format_ in formats or []}
        overrides["outputs"] = {
            "generate_txt": "txt" in selected,
            "generate_srt": "srt" in selected,
            "generate_vtt": "vtt" in selected,
            "generate_segments_json": segments,
        }
    elif segments:
        overrides["outputs"] = {"generate_segments_json": True}
    if keep_temp:
        overrides["runtime"] = {"keep_temp_on_success": True}
    return overrides


def _expected_error(error: ApplicationError) -> None:
    typer.echo(f"Error: {error}", err=True)
    if isinstance(error, InvalidConfigurationError):
        raise typer.Exit(code=2) from error
    if isinstance(error, MissingCapabilityError):
        raise typer.Exit(code=3) from error
    if isinstance(error, (OutputLockUnavailableError, OutputReservationError)):
        raise typer.Exit(code=7) from error
    if isinstance(error, InvalidCanonicalResultError):
        raise typer.Exit(code=8) from error
    raise typer.Exit(code=4) from error


def _input_selection(
    input_path: Path | None,
    group_paths: list[Path] | None,
    group_id: str | None,
) -> tuple[Path, tuple[Path, ...] | None, str | None]:
    explicit = tuple(normalize_input_path(path) for path in group_paths or ())
    if explicit:
        if input_path is not None:
            raise typer.BadParameter("INPUT cannot be combined with --group")
        if len(explicit) < 2:
            raise typer.BadParameter("--group must be repeated for at least two files")
        if group_id is None or not group_id.strip():
            raise typer.BadParameter("--group-id is required with --group")
        return explicit[0], explicit, group_id.strip()
    if group_id is not None:
        raise typer.BadParameter("--group-id requires --group")
    if input_path is None:
        raise typer.BadParameter("provide INPUT or an explicit --group")
    return normalize_input_path(input_path), None, None


def _optional_user_path(path: Path | None) -> Path | None:
    """Normalize an optional Windows, WSL, POSIX, or relative CLI path."""

    return normalize_input_path(path) if path is not None else None


@app.command("clean")
def clean_command(
    target: Annotated[
        CleanTarget,
        typer.Argument(help="Cleanup scope; the MVP supports only all-workdirs."),
    ],
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="List eligible workspaces without removing them."),
    ] = False,
    confirmed: Annotated[
        bool,
        typer.Option("--yes", help="Confirm removal of every listed eligible workspace."),
    ] = False,
    older_than_days: Annotated[
        int,
        typer.Option(
            "--older-than",
            min=0,
            help="Select workspaces at least this many days old.",
        ),
    ] = 0,
) -> None:
    """Safely preview or remove marker-verified application workspaces."""

    if dry_run == confirmed:
        raise typer.BadParameter("choose exactly one of --dry-run or --yes")
    assert target is CleanTarget.ALL_WORKDIRS
    try:
        config = load_config(explicit_path=config_path)
        outcome = clean_all_workdirs(
            config=config,
            older_than_days=older_than_days,
            dry_run=dry_run,
        )
    except ApplicationError as error:
        _expected_error(error)
    action = "WOULD REMOVE" if outcome.dry_run else "REMOVED"
    for path in outcome.paths:
        typer.echo(f"{action} {path}")
    typer.echo(
        f"SUMMARY selected={len(outcome.paths)} removed="
        f"{0 if outcome.dry_run else len(outcome.paths)}"
    )


@app.command("inspect")
def inspect_command(
    input_path: Annotated[
        Path | None,
        typer.Argument(help="Audio file or directory to inspect.", metavar="INPUT"),
    ] = None,
    group_paths: Annotated[
        list[Path] | None,
        typer.Option("--group", help="Explicit source file; repeat for each group member."),
    ] = None,
    group_id: Annotated[
        str | None,
        typer.Option("--group-id", help="Collision-safe output identity for an explicit group."),
    ] = None,
    recursive: Annotated[
        bool | None,
        typer.Option("--recursive", help="Inspect supported files in subdirectories."),
    ] = None,
    language: Annotated[
        RequestedLanguage | None,
        typer.Option("--language", help="Transcription language: pl, en, or auto."),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    channel_mode: Annotated[
        RequestedChannelMode | None,
        typer.Option("--channel-mode", help="Override automatic channel classification."),
    ] = None,
    speaker_count: Annotated[
        str | None,
        typer.Option("--speaker-count", help="Expected speakers: 'auto' or a positive integer."),
    ] = None,
    allow_duration_mismatch: Annotated[
        bool,
        typer.Option(
            "--allow-duration-mismatch",
            help="Allow grouped-source duration differences above the error threshold.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the complete inspection result as JSON."),
    ] = False,
) -> None:
    """Inspect and classify audio without loading transcription models."""

    try:
        selected_input, explicit_group_paths, explicit_group_id = _input_selection(
            input_path, group_paths, group_id
        )
        parsed_speaker_count = _speaker_count(speaker_count)
        config = load_config(
            explicit_path=config_path,
            cli_overrides=_inspection_overrides(
                recursive=recursive,
                language=language,
                channel_mode=channel_mode,
                speaker_count=parsed_speaker_count,
            ),
        )
        result = inspect_input(
            selected_input,
            config=config,
            allow_duration_mismatch=allow_duration_mismatch,
            explicit_group_paths=explicit_group_paths,
            explicit_group_id=explicit_group_id,
        )
    except ApplicationError as error:
        _expected_error(error)

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"Input: {result.discovery.input_path}")
    typer.echo(f"Episodes: {len(result.episodes)}")
    typer.echo(f"Skipped paths: {len(result.discovery.skipped)}")
    for episode in result.episodes:
        typer.echo(
            f"\n{episode.job_id}: {episode.duration_ms} ms, {len(episode.sources)} source(s)"
        )
        for source in episode.sources:
            classification = source.channel_classification
            typer.echo(
                f"  {source.fingerprint.filename}: {source.stream.channels} channel(s), "
                f"detected={classification.detected_mode.value}, "
                f"processing={classification.processing_mode.value}"
            )
        for warning in episode.warnings:
            typer.echo(f"  WARNING {warning.code.value}: {warning.message}")


def _planned_paths(job: JobOutputPlan) -> tuple[Path, ...]:
    if job.outputs is None:
        return ()
    return tuple(
        path
        for path in (
            job.outputs.results,
            job.outputs.transcript,
            job.outputs.subtitles_srt,
            job.outputs.subtitles_vtt,
            job.outputs.segments,
        )
        if path is not None
    )


@app.command("dry-run")
def dry_run_command(
    input_path: Annotated[
        Path | None,
        typer.Argument(help="Audio file or directory to plan.", metavar="INPUT"),
    ] = None,
    group_paths: Annotated[
        list[Path] | None,
        typer.Option("--group", help="Explicit source file; repeat for each group member."),
    ] = None,
    group_id: Annotated[
        str | None,
        typer.Option("--group-id", help="Collision-safe output identity for an explicit group."),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Plan final outputs in this directory."),
    ] = None,
    recursive: Annotated[
        bool | None,
        typer.Option("--recursive", help="Inspect supported files in subdirectories."),
    ] = None,
    language: Annotated[
        RequestedLanguage | None,
        typer.Option("--language", help="Transcription language: pl, en, or auto."),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    channel_mode: Annotated[
        RequestedChannelMode | None,
        typer.Option("--channel-mode", help="Override automatic channel classification."),
    ] = None,
    speaker_count: Annotated[
        str | None,
        typer.Option(
            "--speaker-count",
            help="Use one speaker, an exact positive count, or 'auto'.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Plan a new result version even for a duplicate."),
    ] = False,
    allow_duration_mismatch: Annotated[
        bool,
        typer.Option(
            "--allow-duration-mismatch",
            help="Allow grouped-source duration differences above the error threshold.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the complete execution plan as JSON."),
    ] = False,
) -> None:
    """Plan a run without creating outputs, workdirs, or loading models."""

    try:
        selected_input, explicit_group_paths, explicit_group_id = _input_selection(
            input_path, group_paths, group_id
        )
        parsed_speaker_count = _speaker_count(speaker_count)
        config = load_config(
            explicit_path=config_path,
            cli_overrides=_inspection_overrides(
                recursive=recursive,
                language=language,
                channel_mode=channel_mode,
                speaker_count=parsed_speaker_count,
            ),
        )
        result = dry_run(
            selected_input,
            config=config,
            output_directory=_optional_user_path(output_directory),
            force=force,
            allow_duration_mismatch=allow_duration_mismatch,
            explicit_group_paths=explicit_group_paths,
            explicit_group_id=explicit_group_id,
        )
    except ApplicationError as error:
        _expected_error(error)

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"Output directory: {result.output_directory}")
    episodes = {episode.job_id: episode for episode in result.inspection.episodes}
    for job in result.jobs:
        episode = episodes[job.job_id]
        typer.echo(f"\n{job.decision.value.upper()} {job.job_id}")
        typer.echo(f"  language: {result.language.value}")
        for source in episode.sources:
            speaker = source.speaker_label or source.speaker_id
            typer.echo(f"  source: {source.fingerprint.filename} ({speaker})")
            typer.echo(
                f"    channels: detected={source.channel_classification.detected_mode.value}, "
                f"processing={source.channel_classification.processing_mode.value}"
            )
        if job.outputs is not None:
            typer.echo(f"  result version: {job.outputs.result_version}")
            for path in _planned_paths(job):
                typer.echo(f"  output: {path}")
        elif job.existing_result is not None:
            typer.echo(f"  existing result: {job.existing_result.path}")
        for warning in (*episode.warnings, *job.warnings):
            typer.echo(f"  WARNING {warning.code.value}: {warning.message}")


@app.command("export")
def export_command(
    results_json: Annotated[
        Path,
        typer.Argument(help="Completed canonical results JSON.", metavar="RESULTS_JSON"),
    ],
    formats: Annotated[
        list[ExportFormat] | None,
        typer.Option("--format", help="Export format; may be repeated."),
    ] = None,
    segments: Annotated[
        bool,
        typer.Option("--segments", help="Generate the optional segments JSON export."),
    ] = False,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write exports to this directory."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Create the first free later export version."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    subtitle_preset: Annotated[
        RequestedSubtitlePreset,
        typer.Option("--subtitle-preset", help="Subtitle readability preset."),
    ] = RequestedSubtitlePreset.YOUTUBE,
    speaker_labels: Annotated[
        RequestedSpeakerLabels | None,
        typer.Option("--speaker-labels", help="Subtitle speaker-label behavior."),
    ] = None,
    revision: Annotated[
        str,
        typer.Option(
            "--revision",
            help="Corrected transcript selection: none, latest, or a revision JSON path.",
        ),
    ] = "none",
) -> None:
    """Regenerate exports from canonical JSON without opening source audio."""

    try:
        config = load_config(explicit_path=config_path)
        subtitles_config = config.subtitles.model_copy(
            update={
                "preset": subtitle_preset.value,
                **({"speaker_labels": speaker_labels.value} if speaker_labels is not None else {}),
            }
        )
        requested = list(formats or [])
        if segments:
            requested.append(ExportFormat.SEGMENTS)
        if not requested:
            requested = [
                format_
                for enabled, format_ in (
                    (config.outputs.generate_txt, ExportFormat.TXT),
                    (config.outputs.generate_srt, ExportFormat.SRT),
                    (config.outputs.generate_vtt, ExportFormat.VTT),
                    (config.outputs.generate_segments_json, ExportFormat.SEGMENTS),
                )
                if enabled
            ]
        selected_revision: str | Path = revision
        if revision not in {"none", "latest"}:
            selected_revision = normalize_input_path(revision)
        outcome = export_result(
            normalize_input_path(results_json),
            formats=tuple(requested),
            output_directory=_optional_user_path(output_directory),
            force=force,
            subtitles_config=subtitles_config,
            revision=selected_revision,
        )
    except ApplicationError as error:
        _expected_error(error)

    typer.echo(f"Export version: {outcome.result_version}")
    if outcome.revision_number is not None:
        typer.echo(f"Revision number: {outcome.revision_number}")
    for path in outcome.written:
        typer.echo(f"WROTE {path}")
    for path in outcome.skipped:
        typer.echo(f"SKIP {path}")


@app.command("transcribe")
def transcribe_command(
    input_path: Annotated[
        Path | None,
        typer.Argument(help="Audio file or directory to transcribe.", metavar="INPUT"),
    ] = None,
    group_paths: Annotated[
        list[Path] | None,
        typer.Option("--group", help="Explicit source file; repeat for each group member."),
    ] = None,
    group_id: Annotated[
        str | None,
        typer.Option("--group-id", help="Collision-safe output identity for an explicit group."),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write results and exports to this directory."),
    ] = None,
    recursive: Annotated[
        bool | None,
        typer.Option("--recursive", help="Include supported files in subdirectories."),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    language: Annotated[
        RequestedLanguage | None,
        typer.Option("--language", help="Transcription language: pl, en, or auto."),
    ] = None,
    channel_mode: Annotated[
        RequestedChannelMode | None,
        typer.Option("--channel-mode", help="Override automatic channel classification."),
    ] = None,
    speaker_count: Annotated[
        str | None,
        typer.Option(
            "--speaker-count",
            help="Use one speaker, an exact positive count, or 'auto'.",
        ),
    ] = None,
    speaker: Annotated[
        str | None,
        typer.Option("--speaker", help="Explicit label for one single-speaker source."),
    ] = None,
    speaker_maps: Annotated[
        list[str] | None,
        typer.Option(
            "--speaker-map",
            help="Explicit SOURCE=NAME label; SOURCE is an exact filename; may be repeated.",
        ),
    ] = None,
    preset: Annotated[
        RequestedPreset,
        typer.Option("--preset", help="Select the transcription preset."),
    ] = RequestedPreset.ACCURATE,
    formats: Annotated[
        list[RequestedTranscribeFormat] | None,
        typer.Option("--format", help="Generated text format; may be repeated."),
    ] = None,
    segments: Annotated[
        bool,
        typer.Option("--segments", help="Generate the optional segments JSON export."),
    ] = False,
    keep_temp: Annotated[
        bool,
        typer.Option("--keep-temp", help="Retain the owned workspace after success."),
    ] = False,
    non_interactive: Annotated[
        bool,
        typer.Option("--non-interactive", help="Disable all interactive behavior."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Create a new result version for a duplicate input."),
    ] = False,
    allow_duration_mismatch: Annotated[
        bool,
        typer.Option(
            "--allow-duration-mismatch",
            help="Allow grouped-source duration differences above the error threshold.",
        ),
    ] = False,
) -> None:
    """Transcribe audio with pinned local models."""

    config = None
    try:
        selected_input, explicit_group_paths, explicit_group_id = _input_selection(
            input_path, group_paths, group_id
        )
        parsed_speaker_count = _speaker_count(speaker_count)
        parsed_speaker_map = _speaker_mapping(speaker_maps)
        if speaker is not None and not speaker.strip():
            raise typer.BadParameter("speaker label must not be empty")
        if speaker is not None and (selected_input.is_dir() or explicit_group_paths is not None):
            raise typer.BadParameter("--speaker requires one input file")
        if speaker is not None and parsed_speaker_count not in {None, 1}:
            raise typer.BadParameter("--speaker requires --speaker-count 1")
        config = load_config(
            explicit_path=config_path,
            cli_overrides=_transcribe_overrides(
                recursive=bool(recursive) if selected_input.is_dir() else False,
                language=language,
                channel_mode=channel_mode,
                speaker_count=1 if speaker is not None else parsed_speaker_count,
                preset=preset,
                formats=formats,
                segments=segments,
                keep_temp=keep_temp,
                non_interactive=non_interactive,
            ),
        )
        output_guard = (
            redirect_stdout(sys.stderr) if config.runtime.log_format == "jsonl" else nullcontext()
        )
        with output_guard:
            if selected_input.is_dir() and explicit_group_paths is None:
                batch = transcribe_batch(
                    selected_input,
                    config=config,
                    output_directory=_optional_user_path(output_directory),
                    force=force,
                    allow_duration_mismatch=allow_duration_mismatch,
                    speaker_map=parsed_speaker_map,
                )
            else:
                outcome = transcribe_one(
                    selected_input,
                    config=config,
                    output_directory=_optional_user_path(output_directory),
                    force=force,
                    allow_duration_mismatch=allow_duration_mismatch,
                    speaker_label=speaker.strip() if speaker is not None else None,
                    speaker_map=parsed_speaker_map,
                    explicit_group_paths=explicit_group_paths,
                    explicit_group_id=explicit_group_id,
                )
    except ApplicationError as error:
        if config is not None and config.runtime.log_format == "jsonl":
            _emit_jsonl(
                level="error",
                event="TRANSCRIPTION_FAILED",
                run_id=None,
                job_id=None,
                stage="complete",
                elapsed_ms=None,
                context={
                    "error_type": type(error).__name__,
                    "message": str(error),
                },
            )
        _expected_error(error)

    assert config is not None
    if selected_input.is_dir() and explicit_group_paths is None:
        _print_batch_outcome(batch, log_format=config.runtime.log_format)
    else:
        _print_transcription_outcome(outcome, log_format=config.runtime.log_format)


def _print_transcription_outcome(
    outcome: TranscriptionOutcome, *, log_format: str = "text"
) -> None:
    if log_format == "jsonl":
        _emit_jsonl(
            level="info",
            event="TRANSCRIPTION_COMPLETED"
            if outcome.decision is PlanDecision.PROCESS
            else "TRANSCRIPTION_SKIPPED",
            run_id=outcome.run_id,
            job_id=outcome.job_id,
            stage="complete",
            elapsed_ms=outcome.elapsed_ms,
            context={
                "decision": outcome.decision.value,
                "result_path": str(outcome.result_path),
                "exports_written": [str(path) for path in outcome.exports.written]
                if outcome.exports is not None
                else [],
                "exports_skipped": [str(path) for path in outcome.exports.skipped]
                if outcome.exports is not None
                else [],
            },
        )
        return
    typer.echo(f"{outcome.decision.value.upper()} {outcome.job_id}")
    typer.echo(f"RESULT {outcome.result_path}")
    if outcome.exports is not None:
        for path in outcome.exports.written:
            typer.echo(f"WROTE {path}")
        for path in outcome.exports.skipped:
            typer.echo(f"SKIP {path}")


def _print_batch_outcome(outcome: BatchTranscriptionOutcome, *, log_format: str = "text") -> None:
    if log_format == "jsonl":
        for job in outcome.jobs:
            _emit_jsonl(
                level="error" if job.status == "failed" else "info",
                event=f"JOB_{job.status.upper()}",
                run_id=job.run_id,
                job_id=job.job_id,
                stage="complete",
                elapsed_ms=job.elapsed_ms,
                context={
                    "result_path": str(job.result_path) if job.result_path is not None else None,
                    "failure_code": job.failure_code,
                    "failure_message": job.failure_message,
                },
            )
        _emit_jsonl(
            level="error" if outcome.failed else "info",
            event="BATCH_SUMMARY",
            run_id=None,
            job_id=None,
            stage="complete",
            elapsed_ms=sum(job.elapsed_ms or 0 for job in outcome.jobs),
            context={
                "output_directory": str(outcome.output_directory),
                "completed": outcome.completed,
                "skipped": outcome.skipped,
                "failed": outcome.failed,
                "cancelled": outcome.cancelled,
            },
        )
        if outcome.cancelled:
            raise typer.Exit(code=6)
        if outcome.failed:
            raise typer.Exit(code=5)
        return
    typer.echo(f"Output directory: {outcome.output_directory}")
    for job in outcome.jobs:
        typer.echo(f"{job.status.upper()} {job.job_id}")
        if job.result_path is not None:
            typer.echo(f"  RESULT {job.result_path}")
        if job.failure_code is not None:
            typer.echo(f"  ERROR {job.failure_code}: {job.failure_message}")
    typer.echo(
        f"SUMMARY completed={outcome.completed} skipped={outcome.skipped} "
        f"failed={outcome.failed} cancelled={outcome.cancelled}"
    )
    if outcome.cancelled:
        raise typer.Exit(code=6)
    if outcome.failed:
        raise typer.Exit(code=5)


def _emit_jsonl(
    *,
    level: str,
    event: str,
    run_id: object,
    job_id: str | None,
    stage: str,
    elapsed_ms: int | None,
    context: dict[str, object],
) -> None:
    typer.echo(
        json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": level,
                "event": event,
                "run_id": str(run_id) if run_id is not None else None,
                "job_id": job_id,
                "source": None,
                "stage": stage,
                "elapsed_ms": elapsed_ms,
                "context": context,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


def main() -> None:
    """Run the command-line adapter."""

    app()
