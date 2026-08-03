"""Tests for the Phase 5 transcribe terminal adapter."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ewp_transcripts import cli
from ewp_transcripts.application import TranscriptionOutcome
from ewp_transcripts.cli import app
from ewp_transcripts.domain.enums import PlanDecision


def test_transcribe_cli_applies_single_speaker_scope_and_prints_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "episode.wav"
    source.write_bytes(b"audio")
    result_path = tmp_path / "output" / "episode_results.json"
    observed = {}

    def run(input_path, *, config, output_directory, force, allow_duration_mismatch):
        observed.update(
            input_path=input_path,
            speaker_count=config.diarization.speaker_count,
            output_directory=output_directory,
            force=force,
            allow_duration_mismatch=allow_duration_mismatch,
        )
        return TranscriptionOutcome(
            decision=PlanDecision.PROCESS,
            job_id="episode",
            result_path=result_path,
        )

    monkeypatch.setattr(cli, "transcribe_one", run)
    outcome = CliRunner().invoke(
        app,
        ["transcribe", str(source), "--output-dir", str(tmp_path / "output")],
    )

    assert outcome.exit_code == 0
    assert "PROCESS episode" in outcome.stdout
    assert f"RESULT {result_path}" in outcome.stdout
    assert observed == {
        "input_path": source,
        "speaker_count": 1,
        "output_directory": tmp_path / "output",
        "force": False,
        "allow_duration_mismatch": False,
    }


def test_root_help_lists_transcribe_command() -> None:
    outcome = CliRunner().invoke(app, ["--help"])

    assert outcome.exit_code == 0
    assert "transcribe" in outcome.stdout
