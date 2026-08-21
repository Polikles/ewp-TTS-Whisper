"""Tests for deterministic exact-source translation discovery."""

from pathlib import Path

from ewp_transcripts.translation_discovery import discover_translation_reviews


def test_discover_translation_reviews_ignores_unrelated_files(tmp_path: Path) -> None:
    selected = tmp_path / "episode_en.translation.review.txt"
    selected.write_text("review", encoding="utf-8")
    (tmp_path / "episode.review.txt").write_text("revision", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("notes", encoding="utf-8")

    assert discover_translation_reviews(tmp_path) == (selected.absolute(),)
