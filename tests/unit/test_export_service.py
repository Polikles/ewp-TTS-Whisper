"""Tests for safe model-free export orchestration."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ewp_transcripts import export_service
from ewp_transcripts.application import apply_review_file, prepare_review_file
from ewp_transcripts.config import ApplicationConfig
from ewp_transcripts.domain.errors import InvalidCanonicalResultError
from ewp_transcripts.export_service import ExportFormat, export_result

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = ROOT / "examples/results.example.json"
FIXED_TIME = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


def test_exports_all_formats_without_source_audio_or_models(tmp_path: Path) -> None:
    result_path = tmp_path / "S01E01_results.json"
    result_path.write_bytes(EXAMPLE_PATH.read_bytes())

    outcome = export_result(
        result_path,
        formats=(
            ExportFormat.TXT,
            ExportFormat.SRT,
            ExportFormat.VTT,
            ExportFormat.SEGMENTS,
        ),
        generated_at=FIXED_TIME,
    )

    assert outcome.result_version == 1
    assert {path.name for path in outcome.written} == {
        "S01E01_transcript.txt",
        "S01E01_subtitles.srt",
        "S01E01_subtitles.vtt",
        "S01E01_segments.json",
    }
    assert outcome.skipped == ()
    assert (tmp_path / "S01E01_subtitles.vtt").read_text(encoding="utf-8").startswith("WEBVTT\n")
    segments = json.loads((tmp_path / "S01E01_segments.json").read_text(encoding="utf-8"))
    assert segments["derived_from"]["results_file"] == "S01E01_results.json"
    assert not Path("D:/podcast/S01E01-jan.wav").exists()


def test_existing_export_skips_without_force_and_force_uses_shared_next_version(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "S01E01_results.json"
    result_path.write_bytes(EXAMPLE_PATH.read_bytes())
    transcript = tmp_path / "S01E01_transcript.txt"
    transcript.write_text("keep me", encoding="utf-8")

    unforced = export_result(
        result_path,
        formats=(ExportFormat.TXT, ExportFormat.SRT),
        generated_at=FIXED_TIME,
    )
    forced = export_result(
        result_path,
        formats=(ExportFormat.TXT, ExportFormat.SRT),
        force=True,
        generated_at=FIXED_TIME,
    )

    assert unforced.result_version == 1
    assert unforced.skipped == (transcript,)
    assert (tmp_path / "S01E01_subtitles.srt") in unforced.written
    assert transcript.read_text(encoding="utf-8") == "keep me"
    assert forced.result_version == 2
    assert {path.name for path in forced.written} == {
        "S01E01_transcript_v002.txt",
        "S01E01_subtitles_v002.srt",
    }


def test_export_rejects_invalid_or_noncompleted_results(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")
    with pytest.raises(InvalidCanonicalResultError, match="Cannot read"):
        export_result(invalid, formats=(ExportFormat.TXT,))

    data = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    data["status"] = "running"
    data["completed_at"] = None
    running = tmp_path / "running.json"
    running.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InvalidCanonicalResultError, match="Only completed"):
        export_result(running, formats=(ExportFormat.TXT,))


def test_export_rejects_unsafe_canonical_job_id(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    data["job_id"] = "../escape"
    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(InvalidCanonicalResultError, match="unsafe"):
        export_result(path, formats=(ExportFormat.TXT,))


def test_export_sanitizes_rendering_value_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result_path = tmp_path / "S01E01_results.json"
    result_path.write_bytes(EXAMPLE_PATH.read_bytes())

    def fail(*args, **kwargs):
        raise ValueError("internal rendering detail")

    monkeypatch.setattr(export_service, "build_subtitle_cues", fail)

    with pytest.raises(
        InvalidCanonicalResultError,
        match="Cannot render srt export: invalid renderer input",
    ) as captured:
        export_result(result_path, formats=(ExportFormat.SRT,))
    assert "internal rendering detail" not in str(captured.value)


def test_export_reports_safe_subtitle_invariant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result_path = tmp_path / "S01E01_results.json"
    result_path.write_bytes(EXAMPLE_PATH.read_bytes())

    def fail(*args, **kwargs):
        raise ValueError("ordinary subtitle cues must not overlap")

    monkeypatch.setattr(export_service, "build_subtitle_cues", fail)

    with pytest.raises(
        InvalidCanonicalResultError,
        match="Cannot render vtt export: ordinary subtitle cues must not overlap",
    ):
        export_result(result_path, formats=(ExportFormat.VTT,))


def test_revision_exports_corrected_text_with_distinct_names_and_provenance(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "S01E01_results.json"
    result_path.write_bytes(EXAMPLE_PATH.read_bytes())
    review = prepare_review_file(
        result_path,
        output_directory=tmp_path / "reviews",
    ).path
    review.write_text(
        review.read_text(encoding="utf-8").replace(
            "Today we discuss transcription.",
            "Today we carefully discuss corrected transcription.",
        ),
        encoding="utf-8",
    )
    applied = apply_review_file(review, config=ApplicationConfig())

    outcome = export_result(
        result_path,
        formats=(ExportFormat.TXT, ExportFormat.SRT, ExportFormat.SEGMENTS),
        revision=applied.revision_path,
        generated_at=FIXED_TIME,
    )

    assert outcome.revision_number == 1
    assert {path.name for path in outcome.written} == {
        "S01E01_transcript_revision_001.txt",
        "S01E01_subtitles_revision_001.srt",
        "S01E01_segments_revision_001.json",
    }
    transcript = (tmp_path / "S01E01_transcript_revision_001.txt").read_text(encoding="utf-8")
    assert "carefully discuss corrected transcription" in transcript
    segments = json.loads(
        (tmp_path / "S01E01_segments_revision_001.json").read_text(encoding="utf-8")
    )
    assert segments["derived_from"]["revision_number"] == 1
    assert segments["derived_from"]["revision_file"] == applied.revision_path.name


def test_latest_revision_selection_does_not_change_raw_export(tmp_path: Path) -> None:
    result_path = tmp_path / "S01E01_results.json"
    result_path.write_bytes(EXAMPLE_PATH.read_bytes())
    review = prepare_review_file(result_path, output_directory=tmp_path / "reviews").path
    apply_review_file(review, config=ApplicationConfig())

    revised = export_result(
        result_path,
        formats=(ExportFormat.TXT,),
        revision="latest",
    )
    raw = export_result(result_path, formats=(ExportFormat.TXT,), revision="none")

    assert revised.revision_number == 1
    assert raw.revision_number is None
    assert (tmp_path / "S01E01_transcript.txt").is_file()
