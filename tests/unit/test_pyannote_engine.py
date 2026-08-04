"""Tests for the lazy local-only pyannote adapter without importing ML libraries."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from ewp_transcripts.domain.errors import SpeechEngineError
from ewp_transcripts.engines.pyannote import PyannoteDiarizationEngine


@dataclass(frozen=True)
class Segment:
    start: float
    end: float


class Annotation:
    def __init__(self, rows: tuple[tuple[float, float, str], ...]) -> None:
        self.rows = rows

    def itertracks(self, *, yield_label: bool):
        assert yield_label is True
        return ((Segment(start, end), None, label) for start, end, label in self.rows)


class Output:
    speaker_diarization = Annotation(((1.0, 2.0, "B"), (0.0, 1.5, "A")))
    exclusive_speaker_diarization = Annotation(((0.0, 1.0, "A"), (1.0, 2.0, "B")))


class Pipeline:
    def __init__(self, events: list[object]) -> None:
        self.events = events

    def to(self, device: object) -> None:
        self.events.append(("to", device))

    def __call__(self, audio: Path, **kwargs: object) -> Output:
        self.events.append(("run", audio, kwargs))
        return Output()


class PipelineClass:
    events: list[object] = []

    @classmethod
    def from_pretrained(cls, checkpoint: Path, **kwargs: object) -> Pipeline:
        cls.events.append(("load", checkpoint, kwargs))
        return Pipeline(cls.events)


class Module:
    Pipeline = PipelineClass


class Cuda:
    def __init__(self, events: list[object]) -> None:
        self.events = events

    def is_available(self) -> bool:
        return True

    def empty_cache(self) -> None:
        self.events.append("empty_cache")

    def synchronize(self) -> None:
        self.events.append("synchronize")


class Torch:
    def __init__(self, events: list[object]) -> None:
        self.events = events
        self.cuda = Cuda(events)

    def device(self, name: str) -> str:
        return f"device:{name}"


def test_loads_local_snapshot_runs_exact_count_and_releases(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    events = PipelineClass.events
    events.clear()
    engine = PyannoteDiarizationEngine(
        snapshot,
        revision="revision",
        device="cuda",
        module_loader=lambda: Module(),
        torch_loader=lambda: Torch(events),
    )

    result = engine.diarize(tmp_path / "episode.wav", speaker_count=2)
    engine.close()

    assert events[:3] == [
        ("load", snapshot, {"token": False}),
        ("to", "device:cuda"),
        ("run", tmp_path / "episode.wav", {"num_speakers": 2}),
    ]
    assert [(turn.start_ms, turn.end_ms, turn.speaker_label) for turn in result.turns] == [
        (0, 1500, "A"),
        (1000, 2000, "B"),
    ]
    assert result.exclusive_turns is not None
    assert events[-2:] == ["empty_cache", "synchronize"]


def test_auto_count_omits_num_speakers(tmp_path: Path) -> None:
    events = PipelineClass.events
    events.clear()
    engine = PyannoteDiarizationEngine(
        _snapshot(tmp_path),
        revision="revision",
        device="cuda",
        module_loader=lambda: Module(),
        torch_loader=lambda: Torch(events),
    )

    engine.diarize(tmp_path / "episode.wav", speaker_count=None)

    assert events[2] == ("run", tmp_path / "episode.wav", {})


def test_missing_snapshot_fails_before_module_import(tmp_path: Path) -> None:
    imported = False

    def load_module():
        nonlocal imported
        imported = True
        return Module()

    engine = PyannoteDiarizationEngine(
        tmp_path / "revision",
        revision="revision",
        device="cuda",
        module_loader=load_module,
        torch_loader=lambda: Torch([]),
    )

    with pytest.raises(SpeechEngineError, match="docs/10-wsl2-installation.md"):
        engine.diarize(tmp_path / "episode.wav", speaker_count=2)

    assert imported is False


def test_backend_failure_is_sanitized_and_close_remains_safe(tmp_path: Path) -> None:
    class BrokenPipeline(Pipeline):
        def __call__(self, audio: Path, **kwargs: object) -> Output:
            raise RuntimeError("private backend detail")

    class BrokenClass(PipelineClass):
        @classmethod
        def from_pretrained(cls, checkpoint: Path, **kwargs: object) -> Pipeline:
            return BrokenPipeline([])

    class BrokenModule:
        Pipeline = BrokenClass

    engine = PyannoteDiarizationEngine(
        _snapshot(tmp_path),
        revision="revision",
        device="cuda",
        module_loader=lambda: BrokenModule(),
        torch_loader=lambda: Torch([]),
    )

    with pytest.raises(SpeechEngineError, match="Pyannote diarization execution failed"):
        engine.diarize(tmp_path / "episode.wav", speaker_count=2)
    engine.close()


def _snapshot(tmp_path: Path) -> Path:
    snapshot = tmp_path / "revision"
    snapshot.mkdir(exist_ok=True)
    (snapshot / "config.yaml").write_text("pipeline: fake\n", encoding="utf-8")
    return snapshot
