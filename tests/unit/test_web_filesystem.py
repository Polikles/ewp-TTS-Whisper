from pathlib import Path

import pytest

from ewp_transcripts.web_filesystem import GuiFilesystemController


def test_root_listing_exposes_only_configured_roots(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    controller = GuiFilesystemController((first.resolve(), second.resolve()))

    listing = controller.list("", select="directory")

    assert listing.current_path is None
    assert listing.parent_path is None
    assert listing.roots == (str(first), str(second))
    assert [item.path for item in listing.entries] == [str(first), str(second)]


def test_file_listing_filters_extensions_and_bounds_parent(tmp_path: Path) -> None:
    root = tmp_path / "root"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (nested / "result.json").write_text("{}", encoding="utf-8")
    (nested / "notes.txt").write_text("notes", encoding="utf-8")
    controller = GuiFilesystemController((root.resolve(),))

    listing = controller.list(str(nested), select="file", extensions=("json",))

    assert listing.current_path == str(nested)
    assert listing.parent_path == str(root)
    assert [(item.name, item.kind) for item in listing.entries] == [("result.json", "file")]
    root_listing = controller.list(str(root), select="file", extensions=("json",))
    assert root_listing.parent_path is None


def test_directory_listing_hides_files_and_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "root"
    directory = root / "directory"
    directory.mkdir(parents=True)
    (root / "file.json").write_text("{}", encoding="utf-8")
    (root / "link").symlink_to(directory, target_is_directory=True)
    controller = GuiFilesystemController((root.resolve(),))

    listing = controller.list(str(root), select="directory")

    assert [(item.name, item.kind) for item in listing.entries] == [("directory", "directory")]


def test_outside_paths_symlinks_and_unknown_extensions_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / "link"
    link.symlink_to(outside, target_is_directory=True)
    controller = GuiFilesystemController((root.resolve(),))

    with pytest.raises(ValueError, match="outside"):
        controller.list(str(outside), select="file")
    with pytest.raises(ValueError, match="Symbolic-link"):
        controller.list(str(link), select="file")
    with pytest.raises(ValueError, match="extensions are invalid"):
        controller.list(str(root), select="file", extensions=("exe",))
