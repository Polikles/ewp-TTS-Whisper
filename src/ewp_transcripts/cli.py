"""Terminal adapter for EWP-transcripts."""

from typing import Annotated

import typer

from ewp_transcripts.application import application_version, doctor

app = typer.Typer(
    name="transcriber",
    help="Local-first transcription for edited podcast and training recordings.",
    no_args_is_help=True,
)


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


def main() -> None:
    """Run the command-line adapter."""

    app()
