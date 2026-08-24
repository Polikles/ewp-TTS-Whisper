"""Deterministic YouTube srv3 timed-text rendering."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable

from ewp_transcripts.exporters.subtitles import SubtitleCue


def render_ytt(
    cues: tuple[SubtitleCue, ...],
    *,
    speaker_ids: Iterable[str],
    speaker_palette: tuple[str, ...],
) -> str:
    """Render already-planned cues in YouTube's srv3 timed-text XML profile."""

    if not speaker_palette:
        raise ValueError("YTT speaker palette must not be empty")
    if any(re.fullmatch(r"#[0-9A-Fa-f]{6}", color) is None for color in speaker_palette):
        raise ValueError("YTT speaker palette colors must use #RRGGBB")

    ordered_speakers = tuple(dict.fromkeys((*speaker_ids, "unknown")))
    pen_ids = {speaker_id: str(index + 1) for index, speaker_id in enumerate(ordered_speakers)}
    non_speech_pen_id = str(len(ordered_speakers) + 1)

    root = ET.Element("timedtext", {"format": "3"})
    head = ET.SubElement(root, "head")
    for index, _speaker_id in enumerate(ordered_speakers):
        ET.SubElement(
            head,
            "pen",
            {
                "id": str(index + 1),
                "fc": speaker_palette[index % len(speaker_palette)],
                "fo": "254",
                "fs": "0",
                "sz": "100",
            },
        )
    ET.SubElement(
        head,
        "pen",
        {
            "id": non_speech_pen_id,
            "fc": speaker_palette[0],
            "fo": "254",
            "fs": "0",
            "sz": "100",
            "i": "1",
        },
    )
    ET.SubElement(head, "ws", {"id": "3", "ju": "2", "wfo": "0"})
    ET.SubElement(head, "wp", {"id": "8", "ap": "7", "ah": "50", "av": "90"})

    body = ET.SubElement(root, "body")
    for cue in cues:
        duration_ms = cue.end_ms - cue.start_ms
        if cue.start_ms < 0 or duration_ms <= 0:
            raise ValueError("YTT cue timestamps are invalid")
        speaker_key = cue.speaker_id if cue.speaker_id in pen_ids else "unknown"
        paragraph = ET.SubElement(
            body,
            "p",
            {
                "t": str(cue.start_ms),
                "d": str(duration_ms),
                "wp": "8",
                "ws": "3",
                "p": non_speech_pen_id if cue.kind != "speech" else pen_ids[speaker_key],
            },
        )
        paragraph.text = cue.lines[0]
        for line in cue.lines[1:]:
            line_break = ET.SubElement(paragraph, "br")
            line_break.tail = line

    payload = ET.tostring(root, encoding="unicode", short_empty_elements=True)
    # YouTube's srv3 importer is not a general XML consumer: an upload pilot flattened
    # lines for ElementTree's equivalent ``<br />`` spelling. Match native srv3 bytes.
    payload = payload.replace("<br />", "<br/>")
    document = '<?xml version="1.0" encoding="UTF-8"?>\n' + payload + "\n"
    try:
        ET.fromstring(document)
    except ET.ParseError as error:
        raise ValueError("YTT renderer produced invalid XML") from error
    return document
