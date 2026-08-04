"""Terminal adapter for EWP-transcripts."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from ewp_transcripts.application import (
    BatchTranscriptionOutcome,
    ExportFormat,
    TranscriptionOutcome,
    application_version,
    clean_all_workdirs,
    doctor,
    dry_run,
    export_result,
    inspect_input,
    transcribe_batch,
    transcribe_one,
)
from ewp_transcripts.config import load_config
from ewp_transcripts.domain import JobOutputPlan
from ewp_transcripts.domain.enums import ChannelMode
from ewp_transcripts.domain.errors import (
    ApplicationError,
    InvalidCanonicalResultError,
    InvalidConfigurationError,
    MissingCapabilityError,
    OutputLockUnavailableError,
    OutputReservationError,
)

app = typer.Typer(
    name="transcriber",
    help="Local-first transcription for edited podcast and training recordings.",
    no_args_is_help=True,
)


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


@app.command("doctor")
def doctor_command(
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the diagnostic result as JSON."),
    ] = False,
) -> None:
    """Check the local environment without loading transcription models."""

    result = doctor()
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
    channel_mode: RequestedChannelMode | None,
    speaker_count: str | int | None,
) -> dict[str, object]:
    overrides: dict[str, object] = {}
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
    channel_mode: RequestedChannelMode | None,
    speaker_count: str | int,
    preset: RequestedPreset,
    formats: list[RequestedTranscribeFormat] | None,
    segments: bool,
    keep_temp: bool,
    non_interactive: bool,
) -> dict[str, object]:
    overrides = _inspection_overrides(
        recursive=recursive,
        channel_mode=channel_mode,
        speaker_count=speaker_count,
    )
    general: dict[str, object] = {"preset": preset.value}
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
        Path,
        typer.Argument(help="Audio file or directory to inspect.", metavar="INPUT"),
    ],
    recursive: Annotated[
        bool | None,
        typer.Option("--recursive", help="Inspect supported files in subdirectories."),
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
        parsed_speaker_count = _speaker_count(speaker_count)
        config = load_config(
            explicit_path=config_path,
            cli_overrides=_inspection_overrides(
                recursive=recursive,
                channel_mode=channel_mode,
                speaker_count=parsed_speaker_count,
            ),
        )
        result = inspect_input(
            input_path,
            config=config,
            allow_duration_mismatch=allow_duration_mismatch,
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
        Path,
        typer.Argument(help="Audio file or directory to plan.", metavar="INPUT"),
    ],
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Plan final outputs in this directory."),
    ] = None,
    recursive: Annotated[
        bool | None,
        typer.Option("--recursive", help="Inspect supported files in subdirectories."),
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
        parsed_speaker_count = _speaker_count(speaker_count)
        config = load_config(
            explicit_path=config_path,
            cli_overrides=_inspection_overrides(
                recursive=recursive,
                channel_mode=channel_mode,
                speaker_count=parsed_speaker_count,
            ),
        )
        result = dry_run(
            input_path,
            config=config,
            output_directory=output_directory,
            force=force,
            allow_duration_mismatch=allow_duration_mismatch,
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
        outcome = export_result(
            results_json,
            formats=tuple(requested),
            output_directory=output_directory,
            force=force,
            subtitles_config=subtitles_config,
        )
    except ApplicationError as error:
        _expected_error(error)

    typer.echo(f"Export version: {outcome.result_version}")
    for path in outcome.written:
        typer.echo(f"WROTE {path}")
    for path in outcome.skipped:
        typer.echo(f"SKIP {path}")


@app.command("transcribe")
def transcribe_command(
    input_path: Annotated[
        Path,
        typer.Argument(help="One audio file to transcribe.", metavar="INPUT"),
    ],
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

    try:
        parsed_speaker_count = _speaker_count(speaker_count)
        parsed_speaker_map = _speaker_mapping(speaker_maps)
        if speaker is not None and not speaker.strip():
            raise typer.BadParameter("speaker label must not be empty")
        if speaker is not None and input_path.is_dir():
            raise typer.BadParameter("--speaker requires one input file")
        if speaker is not None and parsed_speaker_count not in {None, 1}:
            raise typer.BadParameter("--speaker requires --speaker-count 1")
        config = load_config(
            explicit_path=config_path,
            cli_overrides=_transcribe_overrides(
                recursive=bool(recursive) if input_path.is_dir() else False,
                channel_mode=channel_mode,
                speaker_count=1 if parsed_speaker_count is None else parsed_speaker_count,
                preset=preset,
                formats=formats,
                segments=segments,
                keep_temp=keep_temp,
                non_interactive=non_interactive,
            ),
        )
        if input_path.is_dir():
            batch = transcribe_batch(
                input_path,
                config=config,
                output_directory=output_directory,
                force=force,
                allow_duration_mismatch=allow_duration_mismatch,
                speaker_map=parsed_speaker_map,
            )
        else:
            outcome = transcribe_one(
                input_path,
                config=config,
                output_directory=output_directory,
                force=force,
                allow_duration_mismatch=allow_duration_mismatch,
                speaker_label=speaker.strip() if speaker is not None else None,
                speaker_map=parsed_speaker_map,
            )
    except ApplicationError as error:
        _expected_error(error)

    if input_path.is_dir():
        _print_batch_outcome(batch)
    else:
        _print_transcription_outcome(outcome)


def _print_transcription_outcome(outcome: TranscriptionOutcome) -> None:
    typer.echo(f"{outcome.decision.value.upper()} {outcome.job_id}")
    typer.echo(f"RESULT {outcome.result_path}")
    if outcome.exports is not None:
        for path in outcome.exports.written:
            typer.echo(f"WROTE {path}")
        for path in outcome.exports.skipped:
            typer.echo(f"SKIP {path}")


def _print_batch_outcome(outcome: BatchTranscriptionOutcome) -> None:
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


def main() -> None:
    """Run the command-line adapter."""

    app()
