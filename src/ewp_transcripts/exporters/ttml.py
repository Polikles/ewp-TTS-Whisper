"""Deterministic conservative TTML profile for YouTube subtitle upload."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable

from ewp_transcripts.exporters.subtitles import SubtitleCue

TTML_NS = "http://www.w3.org/ns/ttml"
TTS_NS = "http://www.w3.org/ns/ttml#styling"
XML_NS = "http://www.w3.org/XML/1998/namespace"

ET.register_namespace("", TTML_NS)
ET.register_namespace("tts", TTS_NS)


def render_ttml(
    cues: tuple[SubtitleCue, ...],
    *,
    language: str,
    speaker_ids: Iterable[str],
    speaker_palette: tuple[str, ...],
) -> str:
    """Render one already-planned subtitle cue to one TTML paragraph."""

    if re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language) is None:
        raise ValueError("TTML language must be a simple BCP 47 tag")
    if not speaker_palette:
        raise ValueError("TTML speaker palette must not be empty")
    if any(re.fullmatch(r"#[0-9A-Fa-f]{6}", color) is None for color in speaker_palette):
        raise ValueError("TTML speaker palette colors must use #RRGGBB")
    ordered_speakers = tuple(dict.fromkeys((*speaker_ids, "unknown")))
    style_ids = _speaker_style_ids(ordered_speakers)
    root = ET.Element(_tag("tt"), {f"{{{XML_NS}}}lang": language})
    head = ET.SubElement(root, _tag("head"))
    styling = ET.SubElement(head, _tag("styling"))
    for index, speaker_id in enumerate(ordered_speakers):
        ET.SubElement(
            styling,
            _tag("style"),
            {
                f"{{{XML_NS}}}id": style_ids[speaker_id],
                f"{{{TTS_NS}}}color": speaker_palette[index % len(speaker_palette)],
            },
        )
    ET.SubElement(
        styling,
        _tag("style"),
        {
            f"{{{XML_NS}}}id": "non-speech",
            f"{{{TTS_NS}}}fontStyle": "italic",
        },
    )
    body = ET.SubElement(root, _tag("body"))
    division = ET.SubElement(body, _tag("div"))
    for cue in cues:
        speaker_key = cue.speaker_id if cue.speaker_id in style_ids else "unknown"
        styles = [style_ids[speaker_key]]
        if cue.kind != "speech":
            styles.append("non-speech")
        paragraph = ET.SubElement(
            division,
            _tag("p"),
            {
                "begin": _clock(cue.start_ms),
                "end": _clock(cue.end_ms),
                "style": " ".join(styles),
                f"{{{TTS_NS}}}color": speaker_palette[
                    ordered_speakers.index(speaker_key) % len(speaker_palette)
                ],
                f"{{{TTS_NS}}}textAlign": "center",
            },
        )
        paragraph.text = cue.lines[0]
        for line in cue.lines[1:]:
            line_break = ET.SubElement(paragraph, _tag("br"))
            line_break.tail = line
    payload = ET.tostring(root, encoding="unicode", short_empty_elements=True)
    document = '<?xml version="1.0" encoding="UTF-8"?>\n' + payload + "\n"
    try:
        ET.fromstring(document)
    except ET.ParseError as error:
        raise ValueError("TTML renderer produced invalid XML") from error
    return document


def _speaker_style_ids(speaker_ids: tuple[str, ...]) -> dict[str, str]:
    assigned: dict[str, str] = {}
    used: set[str] = set()
    for speaker_id in speaker_ids:
        normalized = re.sub(r"[^a-z0-9]+", "-", speaker_id.casefold()).strip("-") or "unknown"
        candidate = f"speaker-{normalized}"
        if candidate in used:
            suffix = hashlib.sha256(speaker_id.encode()).hexdigest()[:8]
            candidate = f"{candidate}-{suffix}"
        used.add(candidate)
        assigned[speaker_id] = candidate
    return assigned


def _clock(milliseconds: int) -> str:
    if milliseconds < 0:
        raise ValueError("TTML cue timestamps are invalid")
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def _tag(local: str) -> str:
    return f"{{{TTML_NS}}}{local}"
