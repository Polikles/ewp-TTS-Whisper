"""Tests for the conservative deterministic YouTube TTML profile."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from ewp_transcripts.domain.canonical import load_canonical_result
from ewp_transcripts.exporters.subtitles import SubtitleCue, build_subtitle_cues
from ewp_transcripts.exporters.ttml import TTML_NS, TTS_NS, XML_NS, render_ttml

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"
PALETTE = ("#FFFFFF", "#00AEEF", "#FFD700")


def test_ttml_maps_each_planned_cue_with_language_timing_and_speaker_style() -> None:
    result = load_canonical_result(EXAMPLE)
    cues = build_subtitle_cues(result)

    rendered = render_ttml(
        cues,
        language=result.transcript.language,
        speaker_ids=(speaker.speaker_id for speaker in result.speakers),
        speaker_palette=PALETTE,
    )
    root = ET.fromstring(rendered)
    paragraphs = root.findall(f".//{{{TTML_NS}}}p")
    styles = root.findall(f".//{{{TTML_NS}}}style")

    assert root.attrib[f"{{{XML_NS}}}lang"] == "en"
    assert len(paragraphs) == len(cues) == 2
    assert paragraphs[0].attrib["begin"] == "00:00:01.240"
    assert paragraphs[0].attrib["end"] == "00:00:03.900"
    assert paragraphs[0].attrib["style"] == "speaker-speaker-001"
    assert paragraphs[0].attrib[f"{{{TTS_NS}}}color"] == "#FFFFFF"
    assert paragraphs[0].attrib[f"{{{TTS_NS}}}textAlign"] == "center"
    assert styles[0].attrib[f"{{{TTS_NS}}}color"] == "#FFFFFF"
    assert (
        render_ttml(
            cues,
            language="en",
            speaker_ids=("speaker_001", "speaker_002"),
            speaker_palette=PALETTE,
        )
        == rendered
    )


def test_ttml_escapes_text_and_uses_separate_non_speech_style() -> None:
    cues = (
        SubtitleCue(
            0,
            1_000,
            ('A & B < "C"',),
            "speaker_001",
            kind="music",
        ),
    )

    rendered = render_ttml(
        cues,
        language="pl",
        speaker_ids=("speaker_001",),
        speaker_palette=PALETTE,
    )
    root = ET.fromstring(rendered)
    paragraph = root.find(f".//{{{TTML_NS}}}p")

    assert paragraph is not None
    assert paragraph.text == 'A & B < "C"'
    assert paragraph.attrib["style"] == "speaker-speaker-001 non-speech"
    assert "&amp;" in rendered and "&lt;" in rendered


def test_ttml_encodes_planned_lines_as_ttml_break_elements() -> None:
    cue = SubtitleCue(0, 1_000, ("First line", "Second line"), "speaker_001")

    root = ET.fromstring(
        render_ttml(
            (cue,),
            language="pl",
            speaker_ids=("speaker_001",),
            speaker_palette=PALETTE,
        )
    )
    paragraph = root.find(f".//{{{TTML_NS}}}p")

    assert paragraph is not None
    line_break = paragraph.find(f"{{{TTML_NS}}}br")
    assert paragraph.text == "First line"
    assert line_break is not None
    assert line_break.tail == "Second line"


def test_ttml_style_ids_are_collision_safe() -> None:
    cues = (
        SubtitleCue(0, 1_000, ("One",), "Speaker A"),
        SubtitleCue(1_100, 2_000, ("Two",), "speaker-a"),
    )

    root = ET.fromstring(
        render_ttml(
            cues,
            language="en-GB",
            speaker_ids=("Speaker A", "speaker-a"),
            speaker_palette=PALETTE,
        )
    )
    style_ids = [
        style.attrib[f"{{{XML_NS}}}id"] for style in root.findall(f".//{{{TTML_NS}}}style")
    ]

    assert len(style_ids) == len(set(style_ids))
    assert style_ids[0] == "speaker-speaker-a"
    assert style_ids[1].startswith("speaker-speaker-a-")


@pytest.mark.parametrize(
    ("language", "palette"),
    [("", PALETTE), ("not_a_tag", PALETTE), ("pl", ()), ("pl", ("blue",))],
)
def test_ttml_rejects_invalid_profile_inputs(language: str, palette: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        render_ttml(
            (SubtitleCue(0, 1_000, ("Text",), None),),
            language=language,
            speaker_ids=(),
            speaker_palette=palette,
        )
