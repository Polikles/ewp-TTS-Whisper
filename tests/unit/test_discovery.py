"""Tests for deterministic file discovery."""

from pathlib import Path

import pytest

from ewp_transcripts.application import discover as application_discover
from ewp_transcripts.config import ApplicationConfig, InputConfig
from ewp_transcripts.discovery import discover_input, normalize_input_path
from ewp_transcripts.domain import DiscoveryResult, DiscoverySkipReason
from ewp_transcripts.domain.errors import InputNotFoundError, SymlinkInputError

SUPPORTED = ("wav", "mp3", "flac", "m4a", "ogg", "opus")


def _discover(path: str | Path, *, recursive: bool = False) -> DiscoveryResult:
    return discover_input(
        path,
        recursive=recursive,
        supported_extensions=SUPPORTED,
    )


def test_single_file_is_kept_even_with_unknown_extension(tmp_path: Path) -> None:
    source = tmp_path / "misleading.data"
    source.write_bytes(b"media probing happens later")

    result = _discover(source)

    assert [item.path for item in result.files] == [source]
    assert result.files[0].suffix == "data"


def test_directory_is_non_recursive_and_filters_suffixes_by_default(tmp_path: Path) -> None:
    (tmp_path / "episode.wav").write_bytes(b"audio")
    (tmp_path / "notes.txt").write_text("notes", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "inside.mp3").write_bytes(b"audio")

    result = _discover(tmp_path)

    assert [item.filename for item in result.files] == ["episode.wav"]
    assert [(item.path.name, item.reason) for item in result.skipped] == [
        ("notes.txt", DiscoverySkipReason.UNSUPPORTED_EXTENSION)
    ]


def test_recursive_discovery_is_explicit(tmp_path: Path) -> None:
    nested = tmp_path / "season"
    nested.mkdir()
    (nested / "episode.mp3").write_bytes(b"audio")

    assert _discover(tmp_path).files == ()
    assert [item.filename for item in _discover(tmp_path, recursive=True).files] == ["episode.mp3"]


def test_natural_order_is_stable_for_unicode_and_numbers(tmp_path: Path) -> None:
    for name in ("żółć10.wav", "Żółć2.wav", "odcinek1.wav", "odcinek11.wav"):
        (tmp_path / name).write_bytes(b"audio")

    result = _discover(tmp_path)

    assert [item.filename for item in result.files] == [
        "odcinek1.wav",
        "odcinek11.wav",
        "Żółć2.wav",
        "żółć10.wav",
    ]


def test_directory_symlink_is_skipped_and_direct_symlink_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.wav"
    target.write_bytes(b"audio")
    link = tmp_path / "linked.wav"
    link.symlink_to(target)

    result = _discover(tmp_path)

    assert [item.filename for item in result.files] == ["target.wav"]
    assert [(item.path, item.reason) for item in result.skipped] == [
        (link, DiscoverySkipReason.SYMLINK)
    ]
    with pytest.raises(SymlinkInputError):
        _discover(link)


def test_missing_input_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(InputNotFoundError, match="does not exist"):
        _discover(tmp_path / "missing.wav")


@pytest.mark.parametrize(
    ("supplied", "expected"),
    [
        (r"D:\Podcasty\Zażółć 2.wav", Path("/mnt/d/Podcasty/Zażółć 2.wav")),
        ("D:/Podcasty/Zażółć 2.wav", Path("/mnt/d/Podcasty/Zażółć 2.wav")),
        ("/mnt/d/Podcasty/Zażółć 2.wav", Path("/mnt/d/Podcasty/Zażółć 2.wav")),
    ],
)
def test_windows_and_wsl_paths_are_normalized(supplied: str, expected: Path) -> None:
    assert normalize_input_path(supplied) == expected


def test_relative_path_uses_supplied_working_directory(tmp_path: Path) -> None:
    assert normalize_input_path("audio/file.wav", cwd=tmp_path) == tmp_path / "audio/file.wav"


def test_application_service_applies_recursive_configuration(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "episode.opus").write_bytes(b"audio")
    config = ApplicationConfig(input=InputConfig(recursive=True))

    result = application_discover(tmp_path, config=config)

    assert [item.filename for item in result.files] == ["episode.opus"]
