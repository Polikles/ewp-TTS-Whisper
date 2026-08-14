"""Tests for the external-editor revision CLI workflow."""

from pathlib import Path

from typer.testing import CliRunner

from ewp_transcripts.cli import app
from ewp_transcripts.domain.errors import RevisionEditorError

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"
runner = CliRunner()


def _base(tmp_path: Path) -> Path:
    path = tmp_path / EXAMPLE.name
    path.write_bytes(EXAMPLE.read_bytes())
    return path


def _change_review(path: Path, *, configured: str) -> None:
    del configured
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")


def test_edit_no_apply_keeps_review_without_revision(monkeypatch, tmp_path: Path) -> None:
    base = _base(tmp_path)
    reviews = tmp_path / "reviews"
    revisions = tmp_path / "revisions"
    monkeypatch.setattr("ewp_transcripts.cli.open_review_in_editor", _change_review)

    result = runner.invoke(
        app,
        [
            "revise",
            "edit",
            str(base),
            "--review-output-dir",
            str(reviews),
            "--output-dir",
            str(revisions),
            "--editor",
            "ignored",
            "--no-apply",
        ],
    )

    assert result.exit_code == 0
    assert "SUMMARY applied=0" in result.stdout
    assert (reviews / "S01E01.review.txt").is_file()
    assert not revisions.exists()


def test_successful_editor_close_applies_review(monkeypatch, tmp_path: Path) -> None:
    base = _base(tmp_path)
    revisions = tmp_path / "revisions"
    monkeypatch.setattr("ewp_transcripts.cli.open_review_in_editor", _change_review)

    result = runner.invoke(
        app,
        [
            "revise",
            "edit",
            str(base),
            "--output-dir",
            str(revisions),
            "--editor",
            "ignored",
        ],
    )

    assert result.exit_code == 0
    assert "SUMMARY applied=1 revision_number=1" in result.stdout
    assert (revisions / "S01E01_revision_001.json").is_file()


def test_failed_editor_keeps_review_but_does_not_apply(monkeypatch, tmp_path: Path) -> None:
    base = _base(tmp_path)
    reviews = tmp_path / "reviews"
    revisions = tmp_path / "revisions"

    def fail_editor(*args, **kwargs):
        raise RevisionEditorError("editor failed")

    monkeypatch.setattr("ewp_transcripts.cli.open_review_in_editor", fail_editor)

    result = runner.invoke(
        app,
        [
            "revise",
            "edit",
            str(base),
            "--review-output-dir",
            str(reviews),
            "--output-dir",
            str(revisions),
            "--editor",
            "ignored",
        ],
    )

    assert result.exit_code == 4
    assert "Error: editor failed" in result.stderr
    assert (reviews / "S01E01.review.txt").is_file()
    assert not revisions.exists()


def test_editor_that_returns_without_changes_does_not_apply(monkeypatch, tmp_path: Path) -> None:
    base = _base(tmp_path)
    reviews = tmp_path / "reviews"
    revisions = tmp_path / "revisions"
    monkeypatch.setattr("ewp_transcripts.cli.open_review_in_editor", lambda *args, **kwargs: None)

    result = runner.invoke(
        app,
        [
            "revise",
            "edit",
            str(base),
            "--review-output-dir",
            str(reviews),
            "--output-dir",
            str(revisions),
            "--editor",
            "ignored",
        ],
    )

    assert result.exit_code == 4
    assert "closed without changing the review" in result.stderr
    assert "no revision was created" in result.stderr
    assert (reviews / "S01E01.review.txt").is_file()
    assert not revisions.exists()
