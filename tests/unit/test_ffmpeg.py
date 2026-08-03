"""Unit tests for safe working-audio preparation."""

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from ewp_transcripts.domain.errors import AudioPreparationError
from ewp_transcripts.media.ffmpeg import prepare_working_audio


def _successful_runner(
    captured: list[str], destination: Path
) -> Callable[[Sequence[str]], subprocess.CompletedProcess[str]]:
    def run(arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
        captured.extend(arguments)
        destination.write_bytes(b"RIFF-controlled-working-audio")
        return subprocess.CompletedProcess(arguments, 0, "", "")

    return run


def test_prepares_selected_channel_without_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source stereo.wav"
    source.write_bytes(b"source remains unchanged")
    destination = tmp_path / "working.wav"
    captured: list[str] = []

    result = prepare_working_audio(
        source,
        destination,
        stream_index=2,
        channel_index=1,
        runner=_successful_runner(captured, destination),
    )

    assert result == destination
    assert captured[:6] == ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-n"]
    assert captured[captured.index("-map") + 1] == "0:2"
    assert captured[captured.index("-af") + 1] == "pan=mono|c0=c1"
    assert captured[captured.index("-ac") + 1] == "1"
    assert captured[captured.index("-ar") + 1] == "16000"
    assert source.read_bytes() == b"source remains unchanged"


def test_downmix_omits_channel_filter(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"source")
    destination = tmp_path / "working.wav"
    captured: list[str] = []

    prepare_working_audio(
        source,
        destination,
        stream_index=0,
        runner=_successful_runner(captured, destination),
    )

    assert "-af" not in captured


def test_rejects_existing_destination_before_running_ffmpeg(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"source")
    destination = tmp_path / "working.wav"
    destination.write_bytes(b"keep")

    with pytest.raises(AudioPreparationError, match="already exists"):
        prepare_working_audio(source, destination, stream_index=0)

    assert destination.read_bytes() == b"keep"


def test_nonzero_exit_is_sanitized(tmp_path: Path) -> None:
    secret = "private recording name or token"

    def runner(arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(arguments, 1, "", secret)

    with pytest.raises(AudioPreparationError) as raised:
        prepare_working_audio(
            tmp_path / "source.wav",
            tmp_path / "working.wav",
            stream_index=0,
            runner=runner,
        )

    assert secret not in str(raised.value)
