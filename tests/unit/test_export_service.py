"""Tests for safe model-free export orchestration."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ewp_transcripts import export_service
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

    with pytest.raises(InvalidCanonicalResultError, match="Cannot render configured exports"):
        export_result(result_path, formats=(ExportFormat.SRT,))
