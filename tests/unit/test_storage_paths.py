"""Tests for pure output path planning."""

from pathlib import Path

import pytest

from ewp_transcripts.config import OutputsConfig
from ewp_transcripts.domain import DiscoveryResult
from ewp_transcripts.domain.errors import UnsafeOutputNameError
from ewp_transcripts.storage import plan_output_paths, resolve_output_directory


def _discovery(input_path: Path) -> DiscoveryResult:
    return DiscoveryResult(input_path=input_path, recursive=False, files=(), skipped=())


def test_single_file_defaults_to_source_directory(tmp_path: Path) -> None:
    source = tmp_path / "episode.wav"
    source.write_bytes(b"audio")

    assert resolve_output_directory(_discovery(source), config=OutputsConfig()) == tmp_path


def test_directory_defaults_to_named_child(tmp_path: Path) -> None:
    assert (
        resolve_output_directory(_discovery(tmp_path), config=OutputsConfig())
        == tmp_path / "output-ewp-transcripts"
    )


def test_explicit_relative_directory_uses_working_directory(tmp_path: Path) -> None:
    result = resolve_output_directory(
        _discovery(tmp_path),
        config=OutputsConfig(),
        explicit_directory=Path("exports"),
        cwd=tmp_path,
    )

    assert result == tmp_path / "exports"


def test_version_one_uses_unsuffixed_role_first_names(tmp_path: Path) -> None:
    paths = plan_output_paths(
        tmp_path,
        job_id="episode",
        version=1,
        config=OutputsConfig(generate_srt=True),
    )

    assert paths.results.name == "episode_results.json"
    assert paths.partial_results.name == "episode_results.partial.json"
    assert paths.failed_results.name == "episode_results.failed.json"
    assert paths.transcript and paths.transcript.name == "episode_transcript.txt"
    assert paths.subtitles_srt and paths.subtitles_srt.name == "episode_subtitles.srt"
    assert paths.segments and paths.segments.name == "episode_segments.json"


def test_later_version_suffix_is_shared_by_complete_output_set(tmp_path: Path) -> None:
    paths = plan_output_paths(
        tmp_path,
        job_id="episode",
        version=2,
        config=OutputsConfig(generate_vtt=True),
    )

    assert paths.results.name == "episode_results_v002.json"
    assert paths.partial_results.name == "episode_results_v002.partial.json"
    assert paths.failed_results.name == "episode_results_v002.failed.json"
    assert paths.transcript and paths.transcript.name == "episode_transcript_v002.txt"
    assert paths.subtitles_vtt and paths.subtitles_vtt.name == "episode_subtitles_v002.vtt"
    assert paths.segments and paths.segments.name == "episode_segments_v002.json"


def test_disabled_derived_outputs_are_not_planned(tmp_path: Path) -> None:
    paths = plan_output_paths(
        tmp_path,
        job_id="episode",
        version=1,
        config=OutputsConfig(
            generate_txt=False,
            generate_srt=False,
            generate_vtt=False,
        ),
    )

    assert paths.transcript is None
    assert paths.subtitles_srt is None
    assert paths.subtitles_vtt is None


@pytest.mark.parametrize("job_id", ["", ".", "..", "../escape", "dir/escape"])
def test_unsafe_job_ids_are_rejected(tmp_path: Path, job_id: str) -> None:
    with pytest.raises(UnsafeOutputNameError):
        plan_output_paths(tmp_path, job_id=job_id, version=1, config=OutputsConfig())
