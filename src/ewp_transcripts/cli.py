"""Terminal adapter for EWP-transcripts."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from ewp_transcripts.application import application_version, doctor, inspect_input
from ewp_transcripts.config import load_config
from ewp_transcripts.domain.enums import ChannelMode
from ewp_transcripts.domain.errors import (
    ApplicationError,
    InvalidConfigurationError,
    MissingCapabilityError,
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


def _expected_error(error: ApplicationError) -> None:
    typer.echo(f"Error: {error}", err=True)
    if isinstance(error, InvalidConfigurationError):
        raise typer.Exit(code=2) from error
    if isinstance(error, MissingCapabilityError):
        raise typer.Exit(code=3) from error
    raise typer.Exit(code=4) from error


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


def main() -> None:
    """Run the command-line adapter."""

    app()
