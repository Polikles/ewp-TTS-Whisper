"""Terminal adapter for EWP-transcripts."""

from typing import Annotated

import typer

from ewp_transcripts.application import application_version

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


def main() -> None:
    """Run the command-line adapter."""

    app()
