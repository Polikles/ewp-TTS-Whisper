"""Tests for lazy WhisperX adapters without importing or loading real ML models."""

import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

from ewp_transcripts.domain.errors import SpeechEngineError
from ewp_transcripts.engines import (
    TranscriptionDraft,
    TranscriptionSegment,
    WhisperXAlignmentEngine,
    WhisperXAsrEngine,
)


class FakeAsrModel:
    def __init__(self, calls: list[tuple[str, object]]) -> None:
        self.calls = calls

    def transcribe(self, audio: object, **kwargs: object) -> Mapping[str, object]:
        self.calls.append(("transcribe", (audio, kwargs)))
        return {
            "language": "pl",
            "segments": [
                {"start": 0.125, "end": 1.234, "text": " Dzień dobry."},
            ],
        }


class FakeWhisperX:
    def __init__(self, calls: list[tuple[str, object]], *, fail: bool = False) -> None:
        self.calls = calls
        self.fail = fail

    def load_audio(self, path: str) -> object:
        self.calls.append(("load_audio", path))
        return "decoded-audio"

    def load_model(self, model: str, device: str, **kwargs: object) -> FakeAsrModel:
        self.calls.append(("load_model", (model, device, kwargs)))
        if self.fail:
            raise RuntimeError("secret backend detail")
        return FakeAsrModel(self.calls)

    def load_align_model(
        self, *, language_code: str, device: str, **kwargs: object
    ) -> tuple[object, Mapping[str, object]]:
        self.calls.append(("load_align_model", (language_code, device, kwargs)))
        return "align-model", {"dictionary": "metadata"}

    def align(
        self,
        transcript: object,
        model: object,
        metadata: Mapping[str, object],
        audio: object,
        device: str,
        **kwargs: object,
    ) -> Mapping[str, object]:
        self.calls.append(("align", (transcript, model, metadata, audio, device, kwargs)))
        return {
            "segments": [
                {
                    "start": 0.125,
                    "end": 1.234,
                    "text": " Dzień dobry.",
                    "words": [
                        {"word": "Dzień", "start": 0.125, "end": 0.5, "score": 0.98},
                        {"word": "dobry."},
                    ],
                }
            ]
        }


def test_asr_loads_pinned_snapshot_locally_and_normalizes_milliseconds(
    tmp_path: Path,
) -> None:
    assert "whisperx" not in sys.modules
    revision = "asr-revision"
    snapshot = tmp_path / revision
    snapshot.mkdir()
    calls: list[tuple[str, object]] = []
    fake = FakeWhisperX(calls)
    engine = WhisperXAsrEngine(
        snapshot,
        revision=revision,
        device="cuda",
        compute_type="float16",
        module_loader=lambda: fake,
    )

    result = engine.transcribe(tmp_path / "working.wav", language="pl", batch_size=4)
    engine.close()

    assert result.segments[0].start_ms == 125
    assert result.segments[0].end_ms == 1234
    load_call = next(value for name, value in calls if name == "load_model")
    assert isinstance(load_call, tuple)
    assert load_call[2]["local_files_only"] is True
    assert "whisperx" not in sys.modules
    assert "torch" not in sys.modules


def test_automatic_language_omits_backend_language_override(tmp_path: Path) -> None:
    revision = "asr-revision"
    snapshot = tmp_path / revision
    snapshot.mkdir()
    calls: list[tuple[str, object]] = []
    engine = WhisperXAsrEngine(
        snapshot,
        revision=revision,
        device="cuda",
        compute_type="float16",
        module_loader=lambda: FakeWhisperX(calls),
    )

    result = engine.transcribe(tmp_path / "working.wav", language="auto", batch_size=4)

    load_call = next(value for name, value in calls if name == "load_model")
    transcribe_call = next(value for name, value in calls if name == "transcribe")
    assert isinstance(load_call, tuple)
    assert isinstance(transcribe_call, tuple)
    assert "language" not in load_call[2]
    assert "language" not in transcribe_call[1]
    assert result.language == "pl"


def test_alignment_uses_local_snapshot_and_preserves_missing_word_times(
    tmp_path: Path,
) -> None:
    revision = "alignment-revision"
    snapshot = tmp_path / revision
    snapshot.mkdir()
    calls: list[tuple[str, object]] = []
    fake = FakeWhisperX(calls)
    engine = WhisperXAlignmentEngine(
        snapshot,
        revision=revision,
        device="cuda",
        module_loader=lambda: fake,
    )
    draft = TranscriptionDraft(
        language="pl",
        segments=(TranscriptionSegment(text=" Dzień dobry.", start_ms=125, end_ms=1234),),
    )

    result = engine.align(tmp_path / "working.wav", draft, language="pl")
    engine.close()

    words = result.segments[0].words
    assert (words[0].start_ms, words[0].end_ms, words[0].confidence) == (125, 500, 0.98)
    assert words[1].start_ms is None and words[1].end_ms is None
    load_call = next(value for name, value in calls if name == "load_align_model")
    assert isinstance(load_call, tuple)
    assert load_call[2]["model_cache_only"] is True
    assert load_call[2]["model_name"] == str(snapshot)


def test_alignment_selects_pinned_english_snapshot(tmp_path: Path) -> None:
    polish_revision = "polish-revision"
    english_revision = "english-revision"
    polish_snapshot = tmp_path / polish_revision
    english_snapshot = tmp_path / english_revision
    polish_snapshot.mkdir()
    english_snapshot.mkdir()
    calls: list[tuple[str, object]] = []
    engine = WhisperXAlignmentEngine(
        polish_snapshot,
        revision=polish_revision,
        english_snapshot=english_snapshot,
        english_revision=english_revision,
        device="cuda",
        module_loader=lambda: FakeWhisperX(calls),
    )
    draft = TranscriptionDraft(
        language="en",
        segments=(TranscriptionSegment(text=" Hello.", start_ms=125, end_ms=1234),),
    )

    engine.align(tmp_path / "working.wav", draft, language="en")

    load_call = next(value for name, value in calls if name == "load_align_model")
    assert isinstance(load_call, tuple)
    assert load_call[0] == "en"
    assert load_call[2]["model_name"] == str(english_snapshot)
    assert engine.model_info.revision == english_revision
    assert engine.model_info.name == "wav2vec2-base-960h"


def test_alignment_rejects_language_without_pinned_model(tmp_path: Path) -> None:
    revision = "polish-revision"
    snapshot = tmp_path / revision
    snapshot.mkdir()
    engine = WhisperXAlignmentEngine(snapshot, revision=revision, device="cuda")
    draft = TranscriptionDraft(
        language="de",
        segments=(TranscriptionSegment(text=" Hallo.", start_ms=0, end_ms=1000),),
    )

    with pytest.raises(SpeechEngineError, match="No pinned local alignment model"):
        engine.align(tmp_path / "working.wav", draft, language="de")


def test_missing_snapshot_fails_before_module_loading(tmp_path: Path) -> None:
    loaded = False

    def loader() -> FakeWhisperX:
        nonlocal loaded
        loaded = True
        return FakeWhisperX([])

    engine = WhisperXAsrEngine(
        tmp_path / "missing-revision",
        revision="missing-revision",
        device="cuda",
        compute_type="float16",
        module_loader=loader,
    )

    with pytest.raises(SpeechEngineError, match="WSL config/MODEL_SETUP.md"):
        engine.transcribe(tmp_path / "audio.wav", language="pl", batch_size=4)

    assert loaded is False


def test_backend_failure_is_sanitized(tmp_path: Path) -> None:
    revision = "asr-revision"
    snapshot = tmp_path / revision
    snapshot.mkdir()
    engine = WhisperXAsrEngine(
        snapshot,
        revision=revision,
        device="cuda",
        compute_type="float16",
        module_loader=lambda: FakeWhisperX([], fail=True),
    )

    with pytest.raises(SpeechEngineError) as raised:
        engine.transcribe(tmp_path / "audio.wav", language="pl", batch_size=4)

    assert "secret backend detail" not in str(raised.value)


def test_alignment_backend_failure_is_sanitized(tmp_path: Path) -> None:
    class BrokenAlignment(FakeWhisperX):
        def align(self, *args: object, **kwargs: object) -> Mapping[str, object]:
            raise RuntimeError("private alignment detail")

    revision = "alignment-revision"
    snapshot = tmp_path / revision
    snapshot.mkdir()
    engine = WhisperXAlignmentEngine(
        snapshot,
        revision=revision,
        device="cuda",
        module_loader=lambda: BrokenAlignment([]),
    )
    draft = TranscriptionDraft(
        language="pl",
        segments=(TranscriptionSegment(text="Tekst.", start_ms=0, end_ms=1000),),
    )

    with pytest.raises(SpeechEngineError, match="WhisperX alignment execution failed") as raised:
        engine.align(tmp_path / "audio.wav", draft, language="pl")

    assert "private alignment detail" not in str(raised.value)
