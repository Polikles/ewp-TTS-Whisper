"""Tests for the Phase 5 single-source pipeline under fake engines."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from jsonschema import Draft202012Validator

from ewp_transcripts.config import ApplicationConfig, DiarizationConfig
from ewp_transcripts.domain import (
    AudioStream,
    ChannelClassification,
    EpisodeInspection,
    InspectedSource,
    JobOutputPlan,
    JobReservation,
    JobStateRecord,
    PlannedOutputPaths,
    SourceFingerprint,
    WorkDirectory,
)
from ewp_transcripts.domain.canonical import CanonicalEnvironment
from ewp_transcripts.domain.enums import ChannelMode, JobStateStatus, PlanDecision
from ewp_transcripts.domain.errors import UnsupportedPipelineScopeError
from ewp_transcripts.engines import (
    AlignedSegment,
    AlignedTranscript,
    AlignedWord,
    EngineModelInfo,
    TranscriptionDraft,
    TranscriptionSegment,
)
from ewp_transcripts.pipeline import process_speaker_stream, run_single_speaker_pipeline
from ewp_transcripts.streams import SpeakerStream

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/results.schema.json"
RUN_ID = UUID("123e4567-e89b-12d3-a456-426614174000")
CREATED_AT = datetime(2026, 8, 3, 10, 0, tzinfo=UTC)
COMPLETED_AT = datetime(2026, 8, 3, 10, 1, tzinfo=UTC)


class FakeAsr:
    model_info = EngineModelInfo(role="asr", name="large-v2", revision="asr-revision")

    def __init__(self, events: list[str], *, fail: bool = False) -> None:
        self.events = events
        self.fail = fail

    def transcribe(self, audio_path: Path, *, language: str, batch_size: int) -> TranscriptionDraft:
        self.events.append(f"asr:{audio_path.name}:{language}:{batch_size}")
        if self.fail:
            raise RuntimeError("controlled ASR failure")
        return TranscriptionDraft(
            language="pl",
            segments=(TranscriptionSegment(text="Dzień dobry.", start_ms=100, end_ms=900),),
        )

    def close(self) -> None:
        self.events.append("asr:close")


class FakeAlignment:
    model_info = EngineModelInfo(
        role="alignment", name="polish-alignment", revision="alignment-revision"
    )

    def __init__(self, events: list[str]) -> None:
        self.events = events

    def align(
        self,
        audio_path: Path,
        transcription: TranscriptionDraft,
        *,
        language: str,
    ) -> AlignedTranscript:
        self.events.append(f"align:{audio_path.name}:{language}:{len(transcription.segments)}")
        return AlignedTranscript(
            language="pl",
            segments=(
                AlignedSegment(
                    text="Dzień dobry.",
                    start_ms=100,
                    end_ms=900,
                    words=(
                        AlignedWord(text="Dzień", start_ms=100, end_ms=400),
                        AlignedWord(text="dobry."),
                    ),
                ),
            ),
        )

    def close(self) -> None:
        self.events.append("align:close")


def test_fake_pipeline_builds_schema_valid_completed_result(tmp_path: Path) -> None:
    inspection, reservation, workspace = _job(tmp_path)
    events: list[str] = []

    def prepare(source: Path, destination: Path, **kwargs: object) -> Path:
        events.append(f"prepare:{source.name}:{kwargs['stream_index']}:{kwargs['channel_index']}")
        destination.write_bytes(b"working audio")
        return destination

    clock_values = iter((0.0, 0.1, 1.0, 1.2, 2.0, 2.3, 3.0, 3.05))
    result = run_single_speaker_pipeline(
        inspection,
        reservation,
        workspace,
        config=ApplicationConfig(diarization=DiarizationConfig(speaker_count=1)),
        environment=_environment(),
        asr_engine=FakeAsr(events),
        alignment_engine=FakeAlignment(events),
        audio_preparer=prepare,
        clock=lambda: next(clock_values),
        now=lambda: COMPLETED_AT,
    )

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(result.model_dump(mode="json"))) == []
    assert result.status == "completed"
    assert result.completed_at == COMPLETED_AT
    assert result.speakers[0].speaker_label == "Speaker1"
    assert result.sources[0].channel_selection == "mono"
    assert [stage.duration_ms for stage in result.processing.stages] == [100, 200, 300, 50]
    assert [word.timestamp_source for word in result.transcript.segments[0].words] == [
        "aligned",
        "interpolated",
    ]
    assert events == [
        "prepare:episode.wav:0:0",
        "asr:source_001-working.wav:pl:4",
        "asr:close",
        "align:source_001-working.wav:pl:1",
        "align:close",
    ]


def test_pipeline_closes_asr_when_transcription_fails(tmp_path: Path) -> None:
    inspection, reservation, workspace = _job(tmp_path)
    events: list[str] = []

    def prepare(source: Path, destination: Path, **kwargs: object) -> Path:
        destination.write_bytes(b"working audio")
        return destination

    with pytest.raises(RuntimeError, match="controlled ASR failure"):
        run_single_speaker_pipeline(
            inspection,
            reservation,
            workspace,
            config=ApplicationConfig(diarization=DiarizationConfig(speaker_count=1)),
            environment=_environment(),
            asr_engine=FakeAsr(events, fail=True),
            alignment_engine=FakeAlignment(events),
            audio_preparer=prepare,
        )

    assert events[-1] == "asr:close"
    assert not any(event.startswith("align:") for event in events)


def test_pipeline_rejects_automatic_speaker_count_before_preparation(tmp_path: Path) -> None:
    inspection, reservation, workspace = _job(tmp_path)

    with pytest.raises(UnsupportedPipelineScopeError, match="speaker_count"):
        run_single_speaker_pipeline(
            inspection,
            reservation,
            workspace,
            config=ApplicationConfig(),
            environment=_environment(),
            asr_engine=FakeAsr([]),
            alignment_engine=FakeAlignment([]),
            audio_preparer=lambda *args, **kwargs: pytest.fail("must not prepare audio"),
        )


def test_processes_one_selected_channel_with_stream_specific_identity(tmp_path: Path) -> None:
    inspection, _, workspace = _job(tmp_path)
    source = inspection.sources[0]
    stream = SpeakerStream(
        source=source,
        source_id="source_001",
        speaker_id="speaker_002",
        speaker_label="Right",
        speaker_source="default",
        channel_index=1,
    )
    events: list[str] = []

    def prepare(source_path: Path, destination: Path, **kwargs: object) -> Path:
        events.append(f"prepare:{kwargs['channel_index']}")
        destination.write_bytes(b"working audio")
        return destination

    processed = process_speaker_stream(
        stream,
        workspace,
        config=ApplicationConfig(diarization=DiarizationConfig(speaker_count=1)),
        asr_engine=FakeAsr(events),
        alignment_engine=FakeAlignment(events),
        working_filename="stream_002-working.wav",
        audio_preparer=prepare,
    )

    segment = processed.normalized.transcript.segments[0]
    assert segment.speaker_id == "speaker_002"
    assert segment.source_ids == ("source_001",)
    assert all(word.speaker_id == "speaker_002" for word in segment.words)
    assert events[0] == "prepare:1"
    assert events[-1] == "align:close"
    assert [stage.name for stage in processed.stages] == [
        "prepare_audio",
        "transcribe",
        "align",
        "normalize",
    ]


def _job(tmp_path: Path) -> tuple[EpisodeInspection, JobReservation, WorkDirectory]:
    source_path = tmp_path / "episode.wav"
    source_path.write_bytes(b"source")
    source = InspectedSource(
        fingerprint=SourceFingerprint(
            path=source_path,
            filename=source_path.name,
            size_bytes=6,
            sha256="a" * 64,
        ),
        stream=AudioStream(index=0, codec="pcm_s16le", sample_rate_hz=48000, channels=1),
        duration_ms=1000,
        channel_mode=ChannelMode.MONO,
        channel_classification=ChannelClassification(
            original_channels=1,
            detected_mode=ChannelMode.MONO,
            processing_mode=ChannelMode.MONO,
            selected_channel_index=0,
        ),
        speaker_id="speaker_001",
    )
    inspection = EpisodeInspection(
        job_id="episode",
        episode_signature_sha256="b" * 64,
        duration_ms=1000,
        sample_rate_hz=48000,
        sources=(source,),
    )
    output = tmp_path / "output"
    outputs = PlannedOutputPaths(
        output_directory=output,
        result_version=1,
        results=output / "episode_results.json",
        partial_results=output / "episode_results.partial.json",
        failed_results=output / "episode_results.failed.json",
    )
    plan = JobOutputPlan(
        job_id="episode",
        episode_signature_sha256="b" * 64,
        decision=PlanDecision.PROCESS,
        outputs=outputs,
    )
    state = JobStateRecord(
        application_version="0.1.0",
        run_id=RUN_ID,
        job_id="episode",
        episode_signature_sha256="b" * 64,
        result_version=1,
        status=JobStateStatus.RUNNING,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )
    reservation = JobReservation(
        plan=plan,
        state=state,
        state_path=outputs.partial_results,
    )
    workspace_path = tmp_path / "work" / str(RUN_ID) / "episode"
    workspace_path.mkdir(parents=True)
    workspace = WorkDirectory(
        work_root=tmp_path / "work",
        run_id=RUN_ID,
        job_id="episode",
        path=workspace_path,
        marker_path=workspace_path / ".ewp-transcripts-work.json",
    )
    return inspection, reservation, workspace


def _environment() -> CanonicalEnvironment:
    return CanonicalEnvironment(
        os="test",
        python="3.12",
        device="fake-cpu",
        compute_type="float16",
        batch_size=4,
    )
