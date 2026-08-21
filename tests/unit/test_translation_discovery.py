"""Tests for deterministic exact-source translation discovery."""

from pathlib import Path

from ewp_transcripts.translation_discovery import (
    discover_translation_reviews,
    discover_translations,
)


def test_discover_translation_reviews_ignores_unrelated_files(tmp_path: Path) -> None:
    selected = tmp_path / "episode_en.translation.review.txt"
    selected.write_text("review", encoding="utf-8")
    (tmp_path / "episode.review.txt").write_text("revision", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("notes", encoding="utf-8")

    assert discover_translation_reviews(tmp_path) == (selected.absolute(),)


def test_discover_translations_excludes_audits_and_other_json(tmp_path: Path) -> None:
    selected = tmp_path / "episode_en_translation_001.json"
    selected.write_text("translation", encoding="utf-8")
    (tmp_path / "episode_en_translation_001_audit.json").write_text("audit", encoding="utf-8")
    (tmp_path / "episode_results.json").write_text("result", encoding="utf-8")

    assert discover_translations(tmp_path) == (selected.absolute(),)
