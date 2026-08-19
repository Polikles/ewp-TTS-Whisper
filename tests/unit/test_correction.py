"""Tests for provider-neutral deterministic correction primitives."""

from dataclasses import replace

from ewp_transcripts.correction import (
    CorrectionChunkConfig,
    DeterministicMockCorrectionProvider,
    build_correction_request,
    plan_correction_chunks,
)
from ewp_transcripts.effective_transcript import EffectiveToken, EffectiveTranscript


def _transcript(count: int, *, speaker_change: int | None = None) -> EffectiveTranscript:
    return EffectiveTranscript(
        language="pl",
        tokens=tuple(
            EffectiveToken(
                token_id=f"word_{index:06d}",
                text=("koniec." if index in {6, 15} else f"token{index}"),
                speaker_id=(
                    "speaker_002"
                    if speaker_change is not None and index >= speaker_change
                    else "speaker_001"
                ),
                source_word_ids=(f"word_{index:06d}",),
                start_ms=index * 100,
                end_ms=index * 100 + 80,
                timing_source="aligned",
                overlap=False,
                active_speaker_ids=("speaker_001",),
            )
            for index in range(count)
        ),
    )


def test_chunk_plan_has_gap_free_single_editable_ownership() -> None:
    transcript = _transcript(23, speaker_change=12)

    chunks = plan_correction_chunks(
        transcript,
        CorrectionChunkConfig(target_tokens=7, max_tokens=9, context_tokens=2),
    )

    owned = [index for chunk in chunks for index in range(chunk.editable_start, chunk.editable_end)]
    assert owned == list(range(23))
    assert all(chunk.editable_end - chunk.editable_start <= 9 for chunk in chunks)
    assert chunks[0].editable_end == 7  # sentence boundary after token 6
    assert chunks[1].context_start == 5
    assert chunks[1].editable_start == 7


def test_chunk_plan_is_deterministic_and_hashes_context() -> None:
    transcript = _transcript(18)
    config = CorrectionChunkConfig(target_tokens=6, max_tokens=8, context_tokens=2)

    first = plan_correction_chunks(transcript, config)
    second = plan_correction_chunks(transcript, config)
    changed = replace(
        transcript,
        tokens=(replace(transcript.tokens[0], text="changed"), *transcript.tokens[1:]),
    )

    assert first == second
    assert plan_correction_chunks(changed, config)[0].content_sha256 != first[0].content_sha256


def test_request_separates_context_and_mock_changes_only_editable_text() -> None:
    transcript = _transcript(18)
    chunks = plan_correction_chunks(
        transcript,
        CorrectionChunkConfig(target_tokens=7, max_tokens=8, context_tokens=2),
    )
    request = build_correction_request(transcript, chunks[1], prompt_id="faithful-pl-v1")
    provider = DeterministicMockCorrectionProvider({"token8": ("OpenAI", "proper_name")})

    response = provider.correct(request)

    assert request.preceding_context
    assert request.following_context
    assert response.operation_id == request.operation_id
    assert response.proposed_changes[0].before == "token8"
    assert response.proposed_changes[0].after == "OpenAI"
    assert "token5" not in response.corrected_text


def test_short_transcript_produces_one_chunk_without_context() -> None:
    transcript = _transcript(3)
    chunk = plan_correction_chunks(transcript)[0]
    request = build_correction_request(transcript, chunk, prompt_id="faithful-pl-v1")

    assert (chunk.editable_start, chunk.editable_end) == (0, 3)
    assert request.preceding_context == ()
    assert request.following_context == ()
