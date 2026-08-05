"""Keep the normative CLI specification synchronized with Typer help."""

import re
from pathlib import Path

from typer.main import get_command

from ewp_transcripts.cli import app

ROOT = Path(__file__).resolve().parents[2]
SPECIFICATION = ROOT / "docs" / "05-cli-specification.md"
COMMANDS = ("doctor", "inspect", "dry-run", "transcribe", "export", "clean")


def _section(document: str, command: str) -> str:
    match = re.search(rf"^## [0-9]+\. `{re.escape(command)}`$", document, re.MULTILINE)
    assert match is not None
    body = document[match.end() :]
    return body.split("\n## ", maxsplit=1)[0]


def test_every_command_help_option_is_named_in_its_specification_section() -> None:
    document = SPECIFICATION.read_text(encoding="utf-8")
    root = get_command(app)

    for command in COMMANDS:
        cli_command = root.commands[command]
        help_options = {
            option
            for parameter in cli_command.params
            for option in getattr(parameter, "opts", ())
            if option.startswith("--") and option != "--help"
        }
        documented_options = set(re.findall(r"--[a-z][a-z-]*", _section(document, command)))
        assert help_options <= documented_options, command
