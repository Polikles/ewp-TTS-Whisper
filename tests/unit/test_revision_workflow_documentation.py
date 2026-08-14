"""Keep the operator revision workflow linked and synchronized with CLI behavior."""

from pathlib import Path

from typer.testing import CliRunner

from ewp_transcripts.cli import app

ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = ROOT / "WSL config" / "REVISE_TRANSCRIPTS.md"
runner = CliRunner()


def test_revision_runbook_covers_complete_safe_workflow() -> None:
    document = RUNBOOK.read_text(encoding="utf-8")

    for command in (
        "revise prepare",
        "revise edit",
        "revise preview",
        "revise apply",
        "revise audit",
        "transcriber export",
    ):
        assert command in document
    for invariant in (
        "never edit or overwrite",
        "plus the accepted\nrevision JSON",
        "/home/linuch/transkrypcje/ewp-transcripts/transcriber.toml",
        '--editor "nano"',
        "environment-variable names, not editor commands",
        "prepare -> edit the review manually in Windows -> apply -> export",
        "Recommended workflow: Windows Notepad",
        "applies only if the review file changed",
        "intentionally stores corrected tokens rather than a second copy",
        "*_segments_revision_NNN.json",
        "--revision latest",
        "--revision none",
        "exit code 5",
        "model-free and audio-free",
    ):
        assert invariant in document

    workflow_positions = [
        document.index("### 2.1. Prepare"),
        document.index("### 2.2. Edit"),
        document.index("### 2.3. Apply"),
        document.index("### 2.4. Export"),
    ]
    assert workflow_positions == sorted(workflow_positions)


def test_operator_index_links_existing_revision_runbook() -> None:
    index = (ROOT / "WSL config" / "README.md").read_text(encoding="utf-8")

    assert "REVISE_TRANSCRIPTS.md" in index
    assert RUNBOOK.is_file()


def test_edit_help_states_automatic_apply_and_exposes_documented_options() -> None:
    result = runner.invoke(app, ["revise", "edit", "--help"])

    assert result.exit_code == 0
    assert "successful editor close applies it unless --no-apply" in result.stdout
    assert "Installed editor command" in result.stdout
    for option in ("--review-output-dir", "--output-dir", "--editor", "--audit", "--no-apply"):
        assert option in result.stdout
