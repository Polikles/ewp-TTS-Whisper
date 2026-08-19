"""Application-boundary tests for network-free automated correction."""

from pathlib import Path

from ewp_transcripts.application import apply_mock_correction, preview_mock_correction
from ewp_transcripts.config import ApplicationConfig, CorrectionConfig, RuntimeConfig
from ewp_transcripts.correction import DeterministicMockCorrectionProvider

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
