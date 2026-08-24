"""Tests for deterministic YouTube srv3 timed-text rendering."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.exporters.subtitles import SubtitleCue, build_subtitle_cues
from ewp_transcripts.exporters.ytt import render_ytt

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"
PALETTE = ("#FFFFFF", "#00AEEF", "#FFD700")


def test_ytt_maps_each_planned_cue_with_timing_position_and_speaker_pen() -> None:
    result = load_canonical_result(EXAMPLE)
    cues = build_subtitle_cues(result)

    rendered = render_ytt(
        cues,
        speaker_ids=(speaker.speaker_id for speaker in result.speakers),
        speaker_palette=PALETTE,
    )
    root = ET.fromstring(rendered)
    paragraphs = root.findall("./body/p")
    pens = root.findall("./head/pen")

    assert root.attrib == {"format": "3"}
    assert len(paragraphs) == len(cues) == 2
    assert paragraphs[0].attrib == {
        "t": "1240",
        "d": "2660",
        "wp": "8",
        "ws": "3",
        "p": "1",
    }
    assert pens[0].attrib["fc"] == "#FFFFFF"
    window_style = root.find("./head/ws")
    position = root.find("./head/wp")
    assert window_style is not None
    assert position is not None
    assert window_style.attrib == {"id": "3", "ju": "2", "wfo": "0"}
    assert position.attrib == {"id": "8", "ap": "7", "ah": "50", "av": "90"}
    assert (
        render_ytt(
            cues,
            speaker_ids=("speaker_001", "speaker_002"),
            speaker_palette=PALETTE,
        )
        == rendered
    )


def test_ytt_escapes_text_and_uses_separate_non_speech_pen() -> None:
    cue = SubtitleCue(0, 1_000, ('A & B < "C"',), "speaker_001", kind="music")

    rendered = render_ytt((cue,), speaker_ids=("speaker_001",), speaker_palette=PALETTE)
    root = ET.fromstring(rendered)
    paragraph = root.find("./body/p")
    pens = root.findall("./head/pen")

    assert paragraph is not None
    assert paragraph.text == 'A & B < "C"'
    assert paragraph.attrib["p"] == pens[-1].attrib["id"]
    assert pens[-1].attrib["i"] == "1"
    assert "&amp;" in rendered and "&lt;" in rendered


def test_ytt_preserves_planned_lines_with_break_elements() -> None:
    cue = SubtitleCue(0, 1_000, ("First line", "Second line"), "speaker_001")

    root = ET.fromstring(render_ytt((cue,), speaker_ids=("speaker_001",), speaker_palette=PALETTE))
    paragraph = root.find("./body/p")

    assert paragraph is not None
    line_break = paragraph.find("br")
    assert paragraph.text == "First line"
    assert line_break is not None
    assert line_break.tail == "Second line"


@pytest.mark.parametrize("palette", [(), ("blue",)])
def test_ytt_rejects_invalid_palette(palette: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        render_ytt(
            (SubtitleCue(0, 1_000, ("Text",), None),),
            speaker_ids=(),
            speaker_palette=palette,
        )


def test_ytt_rejects_invalid_timing() -> None:
    with pytest.raises(ValueError, match="timestamps"):
        render_ytt(
            (SubtitleCue(1_000, 1_000, ("Text",), None),),
            speaker_ids=(),
            speaker_palette=PALETTE,
        )
