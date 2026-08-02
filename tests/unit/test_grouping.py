"""Tests for source fingerprinting and filename-based grouping."""

import hashlib
from pathlib import Path

import pytest

from ewp_transcripts.discovery import discover_input, fingerprint_file, group_discovered_files
from ewp_transcripts.domain import DiscoveredFile
from ewp_transcripts.domain.errors import AmbiguousGroupError

SUPPORTED = ("wav", "mp3")


def _files(root: Path) -> tuple[DiscoveredFile, ...]:
    return discover_input(root, supported_extensions=SUPPORTED).files


def _touch(root: Path, name: str, content: bytes | None = None) -> Path:
    path = root / name
    path.write_bytes(name.encode("utf-8") if content is None else content)
    return path


def test_fingerprint_uses_complete_content_without_modifying_source(tmp_path: Path) -> None:
    content = (b"0123456789" * 1000) + b"end"
    source = _touch(tmp_path, "episode.wav", content)

    fingerprint = fingerprint_file(source, chunk_size=17)

    assert fingerprint.sha256 == hashlib.sha256(content).hexdigest()
    assert fingerprint.size_bytes == len(content)
    assert source.read_bytes() == content


def test_two_speaker_suffixes_form_one_group(tmp_path: Path) -> None:
    _touch(tmp_path, "S01E01_mono_normalized-jan.mp3")
    _touch(tmp_path, "S01E01_mono_normalized-anna.mp3")

    episodes = group_discovered_files(_files(tmp_path))

    assert [episode.job_id for episode in episodes] == ["S01E01_mono_normalized"]
    assert [source.speaker_label for source in episodes[0].sources] == ["anna", "jan"]


def test_single_hyphenated_file_preserves_complete_job_id(tmp_path: Path) -> None:
    _touch(tmp_path, "ai-ethics-introduction.mp3")

    automatic = group_discovered_files(_files(tmp_path))
    explicit_single_speaker = group_discovered_files(_files(tmp_path), speaker_count=1)

    assert automatic[0].job_id == "ai-ethics-introduction"
    assert automatic[0].sources[0].speaker_label is None
    assert explicit_single_speaker[0].job_id == "ai-ethics-introduction"
    assert explicit_single_speaker[0].sources[0].speaker_label == "introduction"


def test_base_file_and_suffixed_file_form_group(tmp_path: Path) -> None:
    _touch(tmp_path, "S01E01.mp3")
    _touch(tmp_path, "S01E01-marta.mp3")

    episodes = group_discovered_files(_files(tmp_path))

    assert len(episodes) == 1
    assert episodes[0].job_id == "S01E01"
    assert [source.speaker_label for source in episodes[0].sources] == ["Speaker1", "marta"]


def test_episode_order_is_natural_and_deterministic(tmp_path: Path) -> None:
    _touch(tmp_path, "episode10.wav")
    _touch(tmp_path, "episode2.wav")
    _touch(tmp_path, "episode1.wav")

    episodes = group_discovered_files(reversed(_files(tmp_path)))

    assert [episode.job_id for episode in episodes] == ["episode1", "episode2", "episode10"]


def test_duplicate_speaker_labels_are_rejected(tmp_path: Path) -> None:
    _touch(tmp_path, "episode-Jan.wav")
    _touch(tmp_path, "episode-jan.mp3")

    with pytest.raises(AmbiguousGroupError, match="Duplicate speaker"):
        group_discovered_files(_files(tmp_path))
