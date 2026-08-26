"""Tests for the non-ML inspection command."""

from pathlib import Path

from typer.testing import CliRunner

from ewp_transcripts.cli import app
from ewp_transcripts.domain import (
    AudioStream,
    ChannelClassification,
    DiscoveryResult,
    EpisodeInspection,
    InspectedSource,
    InspectionResult,
    SourceFingerprint,
)
from ewp_transcripts.domain.enums import ChannelMode, LanguageMode

runner = CliRunner()


def _result(path: Path) -> InspectionResult:
    fingerprint = SourceFingerprint(
        path=path,
        filename=path.name,
        size_bytes=5,
        sha256="a" * 64,
    )
    classification = ChannelClassification(
        original_channels=2,
        detected_mode=ChannelMode.DUAL_MONO,
        processing_mode=ChannelMode.DUAL_MONO,
        selected_channel_index=0,
    )
    source = InspectedSource(
        fingerprint=fingerprint,
        stream=AudioStream(
            index=0,
            codec="pcm_s16le",
            sample_rate_hz=48000,
            channels=2,
            duration_ms=1000,
        ),
        duration_ms=1000,
        channel_mode=ChannelMode.DUAL_MONO,
        channel_classification=classification,
        speaker_id="speaker_001",
    )
    episode = EpisodeInspection(
        job_id="episode",
        episode_signature_sha256="b" * 64,
        duration_ms=1000,
        sample_rate_hz=48000,
        sources=(source,),
    )
    return InspectionResult(
        discovery=DiscoveryResult(
            input_path=path,
            recursive=False,
            files=(),
            skipped=(),
        ),
        episodes=(episode,),
    )


def test_inspect_human_output_reports_channel_decision(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "episode.wav"
    monkeypatch.setattr(
        "ewp_transcripts.cli.inspect_input", lambda *args, **kwargs: _result(source)
    )

    result = runner.invoke(app, ["inspect", str(source)])

    assert result.exit_code == 0
    assert "Episodes: 1" in result.stdout
    assert "detected=dual-mono, processing=dual-mono" in result.stdout


def test_inspect_json_applies_cli_overrides(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "episode.wav"
    captured = {}

    def inspect_stub(*args, **kwargs):
        captured.update(kwargs)
        return _result(source)

    monkeypatch.setattr("ewp_transcripts.cli.inspect_input", inspect_stub)

    result = runner.invoke(
        app,
        [
            "inspect",
            str(source),
            "--recursive",
            "--channel-mode",
            "split-speakers",
            "--language",
            "en",
            "--speaker-count",
            "2",
            "--allow-duration-mismatch",
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    assert '"episodes"' in result.stdout
    config = captured["config"]
    assert config.input.recursive is True
    assert config.channels.mode is ChannelMode.SPLIT_SPEAKERS
    assert config.general.language is LanguageMode.ENGLISH
    assert config.diarization.speaker_count == 2
    assert captured["allow_duration_mismatch"] is True


def test_inspect_rejects_invalid_speaker_count(tmp_path: Path) -> None:
    result = runner.invoke(app, ["inspect", str(tmp_path), "--speaker-count", "zero"])

    assert result.exit_code == 2
    assert "CLI_SPEAKER_COUNT_INVALID" in result.output
