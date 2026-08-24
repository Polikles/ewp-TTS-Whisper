"""Accessible embeddable synchronized transcript fragments."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from dataclasses import dataclass

from ewp_transcripts.effective_transcript import EffectiveTranscript


@dataclass(frozen=True, slots=True)
class HtmlTranscriptUnit:
    speaker_id: str
    text: str
    start_ms: int
    end_ms: int
    kind: str = "speech"


def render_html_transcript(
    transcript: EffectiveTranscript,
    *,
    speaker_labels: Mapping[str, str],
) -> str:
    """Render a deterministic script-free sentence-level HTML fragment."""

    if re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", transcript.language) is None:
        raise ValueError("HTML transcript language must be a simple BCP 47 tag")
    # Imported lazily because translation sentence planning itself reuses the plain-text
    # exporter boundary rules through this package.
    from ewp_transcripts.translation_units import plan_translation_units

    source_units = plan_translation_units(transcript)
    tokens = {token.token_id: token for token in transcript.tokens}
    units = tuple(
        HtmlTranscriptUnit(
            speaker_id=unit.speaker_id,
            text=unit.source_text,
            start_ms=unit.start_ms,
            end_ms=unit.end_ms,
            kind=tokens[unit.source_token_ids[0]].kind,
        )
        for unit in source_units
    )
    return render_html_units(
        language=transcript.language,
        units=units,
        speaker_labels=speaker_labels,
    )


def render_html_units(
    *,
    language: str,
    units: tuple[HtmlTranscriptUnit, ...],
    speaker_labels: Mapping[str, str],
) -> str:
    """Render already planned sentence units into the shared HTML contract."""

    if re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language) is None:
        raise ValueError("HTML transcript language must be a simple BCP 47 tag")
    lines = [f'<section class="ewp-transcript" lang="{html.escape(language)}">']
    current_speaker: str | None = None
    for unit in units:
        if unit.speaker_id != current_speaker:
            if current_speaker is not None:
                lines.append("  </div>")
            current_speaker = unit.speaker_id
            escaped_id = html.escape(unit.speaker_id, quote=True)
            label = html.escape(speaker_labels.get(unit.speaker_id, unit.speaker_id))
            lines.extend(
                (
                    f'  <div class="ewp-transcript__turn" data-speaker-id="{escaped_id}">',
                    f'    <p class="ewp-transcript__speaker">{label}</p>',
                )
            )
        escaped_id = html.escape(unit.speaker_id, quote=True)
        escaped_text = html.escape(unit.text)
        escaped_kind = html.escape(unit.kind, quote=True)
        lines.extend(
            (
                '    <p class="ewp-transcript__cue">',
                '      <button type="button" class="ewp-transcript__seek"'
                f' data-start-ms="{unit.start_ms}" data-end-ms="{unit.end_ms}"'
                f' data-speaker-id="{escaped_id}" data-kind="{escaped_kind}">',
                f"        {escaped_text}",
                "      </button>",
                "    </p>",
            )
        )
    if current_speaker is not None:
        lines.append("  </div>")
    lines.append("</section>")
    return "\n".join(lines) + "\n"
