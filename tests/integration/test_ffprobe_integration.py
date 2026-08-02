"""Real FFmpeg/ffprobe boundary tests without external media."""

import shutil
import subprocess
from pathlib import Path

import pytest

from ewp_transcripts.media import probe_media

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="FFmpeg and ffprobe are required",
)
def test_ffprobe_detects_generated_audio_by_content_without_modifying_it(tmp_path: Path) -> None:
    source = tmp_path / "audio-with-misleading-extension.data"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=0.25",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            str(source),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    before = source.read_bytes()

    result = probe_media(source)

    assert result.path == source
    assert result.duration_ms == 250
    assert result.format_names == ("wav",)
    assert len(result.audio_streams) == 1
    assert result.audio_streams[0].codec == "pcm_s16le"
    assert result.audio_streams[0].sample_rate_hz == 48000
    assert result.audio_streams[0].channels == 1
    assert source.read_bytes() == before
