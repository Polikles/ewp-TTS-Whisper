"""Tests for deterministic translation sentence ownership."""

from ewp_transcripts.effective_transcript import EffectiveToken, EffectiveTranscript
from ewp_transcripts.translation_units import plan_translation_units


def _token(index: int, text: str, speaker: str = "speaker_001") -> EffectiveToken:
    return EffectiveToken(
        token_id=f"word_{index:06d}",
        text=text,
        speaker_id=speaker,
        source_word_ids=(f"word_{index:06d}",),
        start_ms=index * 100,
        end_ms=index * 100 + 80,
        timing_source="aligned",
        overlap=False,
        active_speaker_ids=(speaker,),
    )


def test_units_cover_tokens_once_and_split_sentences() -> None:
    transcript = EffectiveTranscript(
        language="pl",
        tokens=(
            _token(1, "Pierwsze"),
            _token(2, "zdanie."),
            _token(3, "Drugie"),
            _token(4, "zdanie?"),
        ),
    )

    units = plan_translation_units(transcript)

    assert [unit.source_text for unit in units] == ["Pierwsze zdanie.", "Drugie zdanie?"]
    assert [token for unit in units for token in unit.source_token_ids] == [
        token.token_id for token in transcript.tokens
    ]


def test_units_do_not_split_after_abbreviations_or_domains() -> None:
    transcript = EffectiveTranscript(
        language="pl",
        tokens=(
            _token(1, "To"),
            _token(2, "tzw."),
            _token(3, "test"),
            _token(4, "etykawpetli.pl"),
            _token(5, "działa."),
        ),
    )

    units = plan_translation_units(transcript)

    assert len(units) == 1
    assert units[0].source_text == "To tzw. test etykawpetli.pl działa."


def test_speaker_change_is_a_hard_unit_boundary() -> None:
    transcript = EffectiveTranscript(
        language="en",
        tokens=(
            _token(1, "unfinished", "speaker_001"),
            _token(2, "reply.", "speaker_002"),
        ),
    )

    units = plan_translation_units(transcript)

    assert [unit.speaker_id for unit in units] == ["speaker_001", "speaker_002"]
    assert [unit.source_text for unit in units] == ["unfinished", "reply."]
