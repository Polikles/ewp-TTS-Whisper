"""Tests for deterministic translation TXT export."""

from pathlib import Path

from ewp_transcripts.domain.translation import load_transcript_translation
from ewp_transcripts.translation_export import export_translation_text, render_translation_text

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
