"""Tests for provider-neutral deterministic correction primitives."""

from dataclasses import replace
from pathlib import Path

from ewp_transcripts.correction import (
    CorrectionChunkConfig,
    DeterministicMockCorrectionProvider,
    build_correction_request,
    build_mock_correction_revision,
    plan_correction_chunks,
    validate_correction_response,
)
from ewp_transcripts.domain.correction import CorrectionChange
from ewp_transcripts.domain.errors import InvalidCorrectionResponseError
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
    request = build_correction_request(
        transcript,
        chunks[1],
        prompt_id="faithful-pl-v1",
        provider_id="test",
        model_id="test-v1",
    )
    provider = DeterministicMockCorrectionProvider({"token8": ("OpenAI", "proper_name")})

    response = provider.correct(request)

    assert request.preceding_context
    assert request.following_context
    assert response.operation_id == request.operation_id
    assert response.proposed_changes[0].before == "token8"
    assert response.proposed_changes[0].after == "OpenAI"
    assert "token5" not in response.corrected_text
    assert "OpenAI" in validate_correction_response(request, response)


def test_short_transcript_produces_one_chunk_without_context() -> None:
    transcript = _transcript(3)
    chunk = plan_correction_chunks(transcript)[0]
    request = build_correction_request(
        transcript,
        chunk,
        prompt_id="faithful-pl-v1",
        provider_id="test",
        model_id="test-v1",
    )

    assert (chunk.editable_start, chunk.editable_end) == (0, 3)
    assert request.preceding_context == ()
    assert request.following_context == ()


def test_operation_identity_changes_with_provider_or_model() -> None:
    transcript = _transcript(3)
    chunk = plan_correction_chunks(transcript)[0]

    first = build_correction_request(
        transcript,
        chunk,
        prompt_id="faithful-pl-v1",
        provider_id="provider-a",
        model_id="model-1",
    )
    second = build_correction_request(
        transcript,
        chunk,
        prompt_id="faithful-pl-v1",
        provider_id="provider-b",
        model_id="model-1",
    )
    third = build_correction_request(
        transcript,
        chunk,
        prompt_id="faithful-pl-v1",
        provider_id="provider-a",
        model_id="model-2",
    )

    assert len({first.operation_id, second.operation_id, third.operation_id}) == 3


def test_operation_identity_changes_when_prompt_content_changes() -> None:
    transcript = _transcript(3)
    chunk = plan_correction_chunks(transcript)[0]

    first = build_correction_request(
        transcript,
        chunk,
        prompt_id="faithful-pl-v1",
        provider_id="provider-a",
        model_id="model-1",
        prompt_sha256="1" * 64,
    )
    second = build_correction_request(
        transcript,
        chunk,
        prompt_id="faithful-pl-v1",
        provider_id="provider-a",
        model_id="model-1",
        prompt_sha256="2" * 64,
    )

    assert first.operation_id != second.operation_id


def test_response_rejects_mismatched_before_text() -> None:
    transcript = _transcript(3)
    chunk = plan_correction_chunks(transcript)[0]
    request = build_correction_request(
        transcript,
        chunk,
        prompt_id="faithful-pl-v1",
        provider_id="test",
        model_id="test-v1",
    )
    response = (
        DeterministicMockCorrectionProvider()
        .correct(request)
        .model_copy(
            update={
                "corrected_text": "replacement token1 token2",
                "proposed_changes": (
                    CorrectionChange(
                        start_index=0,
                        end_index=1,
                        before="not-the-source",
                        after="replacement",
                        category="asr_lexical",
                    ),
                ),
            }
        )
    )

    try:
        validate_correction_response(request, response)
    except InvalidCorrectionResponseError as error:
        assert "before text" in str(error)
    else:
        raise AssertionError("invalid provider response was accepted")


def test_response_rejects_changes_that_do_not_reconstruct_corrected_text() -> None:
    transcript = _transcript(3)
    chunk = plan_correction_chunks(transcript)[0]
    request = build_correction_request(
        transcript,
        chunk,
        prompt_id="faithful-pl-v1",
        provider_id="test",
        model_id="test-v1",
    )
    response = (
        DeterministicMockCorrectionProvider()
        .correct(request)
        .model_copy(update={"corrected_text": "silently rewritten text"})
    )

    try:
        validate_correction_response(request, response)
    except InvalidCorrectionResponseError as error:
        assert "reconstruct" in str(error)
    else:
        raise AssertionError("unexplained provider rewrite was accepted")


def test_mock_provider_builds_llm_revision_through_existing_aligner() -> None:
    result = Path(__file__).resolve().parents[2] / "examples/results.example.json"
    provider = DeterministicMockCorrectionProvider({"transcription.": ("OpenAI.", "proper_name")})

    revision = build_mock_correction_revision(
        result,
        provider,
        config=CorrectionChunkConfig(target_tokens=4, max_tokens=4, context_tokens=1),
        prompt_id="faithful-en-v1",
    )

    assert revision.provenance.method == "llm"
    assert revision.provenance.llm is not None
    assert revision.provenance.llm.endpoint_kind == "mock"
    assert revision.statistics.substitutions == 1
    assert revision.transcript.tokens[-1].text == "OpenAI."
    assert revision.transcript.tokens[-1].source_word_ids == ("word_000008",)
