"""Tests for accessible embeddable synchronized transcript fragments."""

from ewp_transcripts.domain.canonical import TimedEventKind
from ewp_transcripts.effective_transcript import EffectiveToken, EffectiveTranscript
from ewp_transcripts.exporters.html import render_html_transcript


def _token(
    token_id: str,
    text: str,
    speaker_id: str,
    start_ms: int,
    end_ms: int,
    *,
    kind: TimedEventKind = "speech",
) -> EffectiveToken:
    return EffectiveToken(
        token_id=token_id,
        text=text,
        speaker_id=speaker_id,
        source_word_ids=(token_id,),
        start_ms=start_ms,
        end_ms=end_ms,
        timing_source="canonical",
        overlap=False,
        active_speaker_ids=(speaker_id,),
        kind=kind,
    )


def test_html_fragment_groups_turns_and_exposes_sentence_seek_metadata() -> None:
    transcript = EffectiveTranscript(
        language="pl",
        tokens=(
            _token("word_000001", "Pierwsze", "speaker_001", 100, 300),
            _token("word_000002", "zdanie.", "speaker_001", 310, 700),
            _token("word_000003", "Drugie?", "speaker_001", 800, 1_100),
            _token("word_000004", "Odpowiedź.", "speaker_002", 1_200, 1_600),
        ),
    )

    rendered = render_html_transcript(
        transcript,
        speaker_labels={"speaker_001": "Szymon", "speaker_002": "Damian"},
    )

    assert rendered.startswith('<section class="ewp-transcript" lang="pl">\n')
    assert rendered.count('class="ewp-transcript__turn"') == 2
    assert rendered.count('class="ewp-transcript__speaker"') == 2
    assert rendered.count('class="ewp-transcript__seek"') == 3
    assert 'data-start-ms="100" data-end-ms="700"' in rendered
    assert 'data-speaker-id="speaker_001" data-kind="speech"' in rendered
    assert rendered == render_html_transcript(
        transcript,
        speaker_labels={"speaker_001": "Szymon", "speaker_002": "Damian"},
    )


def test_html_fragment_escapes_untrusted_text_and_contains_no_embedded_behavior() -> None:
    transcript = EffectiveTranscript(
        language="en-GB",
        tokens=(
            _token(
                "word_000001",
                '<script>alert("x")</script>.',
                "speaker_001",
                0,
                1_000,
                kind="note",
            ),
        ),
    )

    rendered = render_html_transcript(
        transcript,
        speaker_labels={"speaker_001": '<img src=x onerror="x">'},
    )

    assert "<script" not in rendered and "<img" not in rendered
    assert "&lt;script&gt;" in rendered and "&lt;img" in rendered
    assert 'data-kind="note"' in rendered
    assert "<style" not in rendered
    assert ' onclick="' not in rendered and ' onerror="' not in rendered


def test_html_fragment_rejects_invalid_language() -> None:
    transcript = EffectiveTranscript(language="not_a_tag", tokens=())

    try:
        render_html_transcript(transcript, speaker_labels={})
    except ValueError as error:
        assert "BCP 47" in str(error)
    else:
        raise AssertionError("invalid language was accepted")
