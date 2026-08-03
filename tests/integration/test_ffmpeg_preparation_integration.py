"""Real FFmpeg working-audio preparation without external media."""

import shutil
import subprocess
from pathlib import Path

import pytest

from ewp_transcripts.media import prepare_working_audio, probe_media

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="FFmpeg and ffprobe are required",
)
def test_prepares_16khz_mono_pcm_and_preserves_source(tmp_path: Path) -> None:
    source = tmp_path / "stereo.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=0.25",
            "-filter_complex",
            "[0:a]asplit=2[left][right];[left][right]join=inputs=2:channel_layout=stereo",
            "-c:a",
            "pcm_s16le",
            str(source),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    before = source.read_bytes()
    destination = tmp_path / "working.wav"

    prepare_working_audio(source, destination, stream_index=0, channel_index=1)
    prepared = probe_media(destination)

    assert prepared.audio_streams[0].codec == "pcm_s16le"
    assert prepared.audio_streams[0].sample_rate_hz == 16_000
    assert prepared.audio_streams[0].channels == 1
    assert source.read_bytes() == before
