"""Application-boundary tests for network-free automated correction."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest

from ewp_transcripts.application import (
    apply_mock_correction,
    preview_correction,
    preview_mock_correction,
    process_mock_correction_batch,
)
from ewp_transcripts.config import (
    ApplicationConfig,
    CorrectionConfig,
    GeneralConfig,
    RuntimeConfig,
)
from ewp_transcripts.correction import DeterministicMockCorrectionProvider
from ewp_transcripts.domain.correction import CorrectionRequest, CorrectionResponse
from ewp_transcripts.domain.errors import CorrectionConsentError

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def _config(tmp_path: Path) -> ApplicationConfig:
    return ApplicationConfig(
        correction=CorrectionConfig(target_tokens=4, max_tokens=4, context_tokens=1),
        runtime=RuntimeConfig(work_root=tmp_path / "work"),
    )


def test_mock_preview_uses_application_config_and_writes_nothing(tmp_path: Path) -> None:
    base = tmp_path / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())
    provider = DeterministicMockCorrectionProvider({"transcription.": ("OpenAI.", "proper_name")})

    outcome = preview_mock_correction(base, config=_config(tmp_path), provider=provider)

    assert outcome.revision.statistics.substitutions == 1
    assert outcome.revision.provenance.llm is not None
    assert outcome.revision.provenance.llm.endpoint_kind == "mock"
    assert sorted(tmp_path.iterdir()) == [base]


def test_mock_apply_publishes_without_modifying_base(tmp_path: Path) -> None:
    base = tmp_path / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())
    before = base.read_bytes()
    provider = DeterministicMockCorrectionProvider({"transcription.": ("OpenAI.", "proper_name")})

    outcome = apply_mock_correction(
        base,
        config=_config(tmp_path),
        provider=provider,
        output_directory=tmp_path / "revisions",
    )

    assert outcome.revision_path.name == "S01E01_revision_001.json"
    assert outcome.revision_path.is_file()
    assert base.read_bytes() == before


def _result(path: Path, job_id: str) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["job_id"] = job_id
    data["episode"]["episode_id"] = job_id
    path.write_text(json.dumps(data), encoding="utf-8")


def test_mock_batch_is_natural_nonrecursive_and_failure_isolated(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    _result(results / "episode10_results.json", "episode10")
    (results / "episode3_results.json").write_text("invalid", encoding="utf-8")
    _result(results / "episode2_results.json", "episode2")
    nested = results / "nested"
    nested.mkdir()
    _result(nested / "episode4_results.json", "episode4")

    outcome = process_mock_correction_batch(
        results,
        config=_config(tmp_path),
        provider=DeterministicMockCorrectionProvider(),
        output_directory=tmp_path / "revisions",
    )

    assert [job.result_path.name for job in outcome.jobs] == [
        "episode2_results.json",
        "episode3_results.json",
        "episode10_results.json",
    ]
    assert [job.status for job in outcome.jobs] == ["applied", "failed", "applied"]
    assert outcome.applied == 2
    assert outcome.failed == 1
    assert outcome.stopped_early is False


def test_mock_batch_preview_obeys_stop_policy_and_writes_nothing(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    (results / "episode2_results.json").write_text("invalid", encoding="utf-8")
    _result(results / "episode10_results.json", "episode10")
    config = ApplicationConfig(
        correction=CorrectionConfig(target_tokens=4, max_tokens=4, context_tokens=1),
        runtime=RuntimeConfig(
            work_root=tmp_path / "work",
            continue_batch_after_error=False,
        ),
    )

    outcome = process_mock_correction_batch(
        results,
        config=config,
        provider=DeterministicMockCorrectionProvider(),
        output_directory=tmp_path / "revisions",
        apply=False,
    )

    assert [job.status for job in outcome.jobs] == ["failed"]
    assert outcome.stopped_early is True
    assert not (tmp_path / "revisions").exists()


@dataclass
class _CountingProvider:
    calls: int = 0

    @property
    def provider_id(self) -> str:
        return "application-counting-mock"

    @property
    def model_id(self) -> str:
        return "v1"

    @property
    def endpoint_kind(self) -> Literal["mock"]:
        return "mock"

    @property
    def endpoint_identity(self) -> str:
        return "in-process"

    def prompt_sha256(self, prompt_id: str) -> str:
        return DeterministicMockCorrectionProvider().prompt_sha256(prompt_id)

    def correct(
        self,
        request: CorrectionRequest,
        *,
        timeout_seconds: float | None = None,
    ) -> CorrectionResponse:
        del timeout_seconds
        self.calls += 1
        return DeterministicMockCorrectionProvider().correct(request)


def test_application_resume_directory_avoids_repeating_chunk_calls(tmp_path: Path) -> None:
    base = tmp_path / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())
    provider = _CountingProvider()
    resume = tmp_path / "resume"

    first = preview_mock_correction(
        base,
        config=_config(tmp_path),
        provider=provider,
        resume_directory=resume,
    )
    calls_after_first = provider.calls
    second = preview_mock_correction(
        base,
        config=_config(tmp_path),
        provider=provider,
        resume_directory=resume,
    )

    assert calls_after_first == 2
    assert provider.calls == calls_after_first
    assert first.revision.transcript == second.revision.transcript
    assert len(tuple(resume.glob("*.json"))) == 2


@dataclass
class _LocalCountingProvider(_CountingProvider):
    @property
    def provider_id(self) -> str:
        return "lm-studio"

    @property
    def endpoint_kind(self) -> Literal["local"]:
        return "local"

    @property
    def endpoint_identity(self) -> str:
        return "http://127.0.0.1:1234/v1"


def _local_config(tmp_path: Path) -> ApplicationConfig:
    return ApplicationConfig(
        general=GeneralConfig(offline=True, interactive=False),
        correction=CorrectionConfig(
            provider="lm-studio",
            model="v1",
            target_tokens=4,
            max_tokens=4,
            context_tokens=1,
            consent_store=tmp_path / "consent.json",
        ),
        runtime=RuntimeConfig(work_root=tmp_path / "work"),
    )


def test_local_provider_rejection_makes_zero_calls(tmp_path: Path) -> None:
    base = tmp_path / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())
    provider = _LocalCountingProvider()

    with pytest.raises(CorrectionConsentError, match="rejected"):
        preview_correction(
            base,
            config=_local_config(tmp_path),
            provider=provider,
            consent_choice="reject",
        )

    assert provider.calls == 0


def test_persisted_local_consent_is_reused_for_exact_scope(tmp_path: Path) -> None:
    base = tmp_path / EXAMPLE.name
    base.write_bytes(EXAMPLE.read_bytes())
    provider = _LocalCountingProvider()
    config = _local_config(tmp_path)

    preview_correction(
        base,
        config=config,
        provider=provider,
        consent_choice="accept_persistently",
    )
    first_calls = provider.calls
    preview_correction(base, config=config, provider=provider)

    assert first_calls == 2
    assert provider.calls == 4
    assert config.correction.consent_store.is_file()
