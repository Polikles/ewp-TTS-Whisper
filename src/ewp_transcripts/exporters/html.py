"""Accessible embeddable synchronized transcript fragments."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping

from ewp_transcripts.effective_transcript import EffectiveTranscript


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

    units = plan_translation_units(transcript)
    tokens = {token.token_id: token for token in transcript.tokens}
    lines = [f'<section class="ewp-transcript" lang="{html.escape(transcript.language)}">']
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
        kind = tokens[unit.source_token_ids[0]].kind
        escaped_id = html.escape(unit.speaker_id, quote=True)
        escaped_text = html.escape(unit.source_text)
        lines.extend(
            (
                '    <p class="ewp-transcript__cue">',
                '      <button type="button" class="ewp-transcript__seek"'
                f' data-start-ms="{unit.start_ms}" data-end-ms="{unit.end_ms}"'
                f' data-speaker-id="{escaped_id}" data-kind="{kind}">',
                f"        {escaped_text}",
                "      </button>",
                "    </p>",
            )
        )
    if current_speaker is not None:
        lines.append("  </div>")
    lines.append("</section>")
    return "\n".join(lines) + "\n"
