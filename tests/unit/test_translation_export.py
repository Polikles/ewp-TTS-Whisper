"""Tests for deterministic translation TXT export."""

from pathlib import Path

from ewp_transcripts.domain.translation import load_transcript_translation
from ewp_transcripts.translation_export import (
    TranslationExportFormat,
    build_translation_subtitle_cues,
    export_translation,
    export_translation_text,
    render_translation_text,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/translation.example.json"


def test_render_translation_text_uses_stable_speaker_blocks() -> None:
    translation = load_transcript_translation(EXAMPLE)

    rendered = render_translation_text(translation)

    assert rendered == (
        "speaker_001:\nWitamy w kolejnym odcinku.\n\n"
        "speaker_002:\nDzisiaj rozmawiamy o transkrypcji.\n"
    )


def test_export_translation_text_writes_then_skips_identical(tmp_path: Path) -> None:
    first = export_translation_text(EXAMPLE, output_directory=tmp_path)
    second = export_translation_text(EXAMPLE, output_directory=tmp_path)

    expected = tmp_path / "S01E01_pl_translation_001.txt"
    assert first.written == (expected,)
    assert second.skipped == (expected,)
    assert expected.read_text(encoding="utf-8").startswith("speaker_001:")


def test_translation_subtitles_stay_inside_unit_timing_and_render(tmp_path: Path) -> None:
    translation = load_transcript_translation(EXAMPLE)

    cues = build_translation_subtitle_cues(translation)
    outcome = export_translation(
        EXAMPLE,
        formats=(TranslationExportFormat.SRT, TranslationExportFormat.VTT),
        output_directory=tmp_path,
    )

    assert cues[0].start_ms == translation.units[0].start_ms
    assert cues[0].end_ms <= translation.units[0].end_ms
    assert cues[-1].end_ms == translation.units[-1].end_ms
    assert {path.suffix for path in outcome.written} == {".srt", ".vtt"}
    assert "00:00:01,240 --> 00:00:03,900" in next(
        path for path in outcome.written if path.suffix == ".srt"
    ).read_text(encoding="utf-8")
