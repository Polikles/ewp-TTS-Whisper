"""Tests for the Phase 5 transcribe terminal adapter."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ewp_transcripts import cli
from ewp_transcripts.application import (
    BatchJobOutcome,
    BatchTranscriptionOutcome,
    TranscriptionOutcome,
)
from ewp_transcripts.cli import app
from ewp_transcripts.domain.enums import LanguageMode, PlanDecision


def test_transcribe_cli_applies_single_speaker_scope_and_prints_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "episode.wav"
    source.write_bytes(b"audio")
    result_path = tmp_path / "output" / "episode_results.json"
    observed = {}

    def run(
        input_path,
        *,
        config,
        output_directory,
        force,
        allow_duration_mismatch,
        speaker_label,
        speaker_map,
    ):
        observed.update(
            input_path=input_path,
            speaker_count=config.diarization.speaker_count,
            output_directory=output_directory,
            force=force,
            allow_duration_mismatch=allow_duration_mismatch,
            speaker_label=speaker_label,
            speaker_map=speaker_map,
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
        "speaker_label": None,
        "speaker_map": {},
    }


def test_transcribe_cli_passes_explicit_speaker_label_and_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "episode.wav"
    source.write_bytes(b"audio")
    observed: list[tuple[str | None, dict[str, str]]] = []

    def run(input_path, *, speaker_label, speaker_map, **kwargs):
        observed.append((speaker_label, speaker_map))
        return TranscriptionOutcome(
            decision=PlanDecision.PROCESS,
            job_id="episode",
            result_path=tmp_path / "episode_results.json",
        )

    monkeypatch.setattr(cli, "transcribe_one", run)

    label = CliRunner().invoke(app, ["transcribe", str(source), "--speaker", "Damian"])
    mapping = CliRunner().invoke(
        app,
        ["transcribe", str(source), "--speaker-map", "episode.wav=Szymon"],
    )

    assert label.exit_code == 0
    assert mapping.exit_code == 0
    assert observed == [("Damian", {}), (None, {"episode.wav": "Szymon"})]


@pytest.mark.parametrize("value", ["episode.wav", "=Damian", "episode.wav="])
def test_transcribe_cli_rejects_invalid_speaker_map(tmp_path: Path, value: str) -> None:
    source = tmp_path / "episode.wav"
    source.write_bytes(b"audio")

    outcome = CliRunner().invoke(app, ["transcribe", str(source), "--speaker-map", value])

    assert outcome.exit_code == 2


def test_root_help_lists_transcribe_command() -> None:
    outcome = CliRunner().invoke(app, ["--help"])

    assert outcome.exit_code == 0
    assert "transcribe" in outcome.stdout


def test_transcribe_cli_accepts_automatic_speaker_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "episode.wav"
    source.write_bytes(b"audio")
    observed: list[str | int] = []

    def run(input_path, *, config, **kwargs):
        observed.append(config.diarization.speaker_count)
        return TranscriptionOutcome(
            decision=PlanDecision.PROCESS,
            job_id="episode",
            result_path=tmp_path / "episode_results.json",
        )

    monkeypatch.setattr(cli, "transcribe_one", run)

    outcome = CliRunner().invoke(app, ["transcribe", str(source), "--speaker-count", "auto"])

    assert outcome.exit_code == 0
    assert observed == ["auto"]


@pytest.mark.parametrize(
    ("requested", "expected"),
    [("pl", LanguageMode.POLISH), ("en", LanguageMode.ENGLISH), ("auto", LanguageMode.AUTO)],
)
def test_transcribe_cli_applies_language_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requested: str,
    expected: LanguageMode,
) -> None:
    source = tmp_path / "episode.wav"
    source.write_bytes(b"audio")
    observed: list[LanguageMode] = []

    def run(input_path, *, config, **kwargs):
        observed.append(config.general.language)
        return TranscriptionOutcome(
            decision=PlanDecision.PROCESS,
            job_id="episode",
            result_path=tmp_path / "episode_results.json",
        )

    monkeypatch.setattr(cli, "transcribe_one", run)

    outcome = CliRunner().invoke(app, ["transcribe", str(source), "--language", requested])

    assert outcome.exit_code == 0
    assert observed == [expected]


def test_transcribe_cli_applies_output_runtime_and_interaction_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "episode.wav"
    source.write_bytes(b"audio")
    observed: dict[str, object] = {}

    def run(input_path, *, config, **kwargs):
        observed.update(
            preset=config.general.preset,
            interactive=config.general.interactive,
            generate_txt=config.outputs.generate_txt,
            generate_srt=config.outputs.generate_srt,
            generate_vtt=config.outputs.generate_vtt,
            generate_segments_json=config.outputs.generate_segments_json,
            keep_temp_on_success=config.runtime.keep_temp_on_success,
        )
        return TranscriptionOutcome(
            decision=PlanDecision.PROCESS,
            job_id="episode",
            result_path=tmp_path / "episode_results.json",
        )

    monkeypatch.setattr(cli, "transcribe_one", run)

    outcome = CliRunner().invoke(
        app,
        [
            "transcribe",
            str(source),
            "--preset",
            "accurate",
            "--format",
            "txt",
            "--segments",
            "--keep-temp",
            "--non-interactive",
        ],
    )

    assert outcome.exit_code == 0
    assert observed == {
        "preset": "accurate",
        "interactive": False,
        "generate_txt": True,
        "generate_srt": False,
        "generate_vtt": False,
        "generate_segments_json": True,
        "keep_temp_on_success": True,
    }


def test_transcribe_segments_flag_adds_to_default_exports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "episode.wav"
    source.write_bytes(b"audio")
    observed: list[tuple[bool, bool, bool, bool]] = []

    def run(input_path, *, config, **kwargs):
        observed.append(
            (
                config.outputs.generate_txt,
                config.outputs.generate_srt,
                config.outputs.generate_vtt,
                config.outputs.generate_segments_json,
            )
        )
        return TranscriptionOutcome(
            decision=PlanDecision.PROCESS,
            job_id="episode",
            result_path=tmp_path / "episode_results.json",
        )

    monkeypatch.setattr(cli, "transcribe_one", run)

    outcome = CliRunner().invoke(app, ["transcribe", str(source), "--segments"])

    assert outcome.exit_code == 0
    assert observed == [(True, True, True, True)]


def test_directory_transcribe_prints_stable_summary_and_partial_failure_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "input"
    source.mkdir()
    destination = tmp_path / "output"

    monkeypatch.setattr(
        cli,
        "transcribe_batch",
        lambda *args, **kwargs: BatchTranscriptionOutcome(
            output_directory=destination,
            jobs=(
                BatchJobOutcome(
                    job_id="first",
                    status="completed",
                    result_path=destination / "first_results.json",
                ),
                BatchJobOutcome(
                    job_id="second",
                    status="failed",
                    failure_code="SPEECH_ENGINE_ERROR",
                    failure_message="controlled failure",
                ),
            ),
        ),
    )

    outcome = CliRunner().invoke(app, ["transcribe", str(source)])

    assert outcome.exit_code == 5
    assert "COMPLETED first" in outcome.stdout
    assert "FAILED second" in outcome.stdout
    assert "ERROR SPEECH_ENGINE_ERROR: controlled failure" in outcome.stdout
    assert "SUMMARY completed=1 skipped=0 failed=1 cancelled=0" in outcome.stdout
