from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from ewp_transcripts.application import apply_correction
from ewp_transcripts.config import ApplicationConfig, RuntimeConfig
from ewp_transcripts.correction import DeterministicMockCorrectionProvider
from ewp_transcripts.web_corrections import (
    GuiCorrectionController,
    GuiCorrectionError,
    _preflight_provider,
)
from ewp_transcripts.web_workflows import GuiWorkflowController

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def mock_runner(result_path: Path, **kwargs: Any) -> Any:
    return apply_correction(
        result_path,
        config=kwargs["config"],
        provider=DeterministicMockCorrectionProvider(),
        output_directory=kwargs["output_directory"],
        resume_directory=kwargs["resume_directory"],
        dictionary=kwargs["dictionary"],
        dictionary_sha256=kwargs["dictionary_sha256"],
        dictionary_project_id=kwargs["dictionary_project_id"],
    )


def controller(tmp_path: Path) -> GuiCorrectionController:
    paths = GuiWorkflowController((tmp_path.resolve(),))
    return GuiCorrectionController(
        config=ApplicationConfig(runtime=RuntimeConfig(work_root=tmp_path / "work")),
        resolve_path=paths.resolve_allowed_path,
        runner=mock_runner,
        preflight=lambda provider, config: None,
    )


def test_gui_correction_publishes_explicit_non_final_candidate(tmp_path: Path) -> None:
    result = tmp_path / EXAMPLE.name
    result.write_bytes(EXAMPLE.read_bytes())

    outcome = controller(tmp_path).generate(
        result=str(result),
        output_directory=str(tmp_path / "candidates"),
        resume_directory=str(tmp_path / "state"),
        provider_name="openrouter",
        model="google/gemini-2.5-flash",
        endpoint="https://openrouter.ai/api/v1",
        allow_remote_endpoint=False,
        allow_cloud=True,
        reasoning_max_tokens=0,
        dictionary_path="",
        project_id="",
        confirmed=True,
    )

    assert outcome["final"] is False
    assert outcome["provider"] == "openrouter"
    assert outcome["model"] == "google/gemini-2.5-flash"
    assert Path(outcome["candidate_path"]).is_file()


def test_gui_correction_requires_consent_and_cloud_opt_in(tmp_path: Path) -> None:
    result = tmp_path / EXAMPLE.name
    result.write_bytes(EXAMPLE.read_bytes())
    service = controller(tmp_path)
    request = {
        "result": str(result),
        "output_directory": str(tmp_path / "candidates"),
        "resume_directory": str(tmp_path / "state"),
        "provider_name": "openrouter",
        "model": "google/gemini-2.5-flash",
        "endpoint": "https://openrouter.ai/api/v1",
        "allow_remote_endpoint": False,
        "allow_cloud": True,
        "reasoning_max_tokens": 0,
        "dictionary_path": "",
        "project_id": "",
    }

    with pytest.raises(GuiCorrectionError) as missing_consent:
        service.generate(**request, confirmed=False)
    assert missing_consent.value.code == "GUI_CORRECTION_CONFIRMATION_REQUIRED"

    with pytest.raises(GuiCorrectionError) as missing_cloud:
        service.generate(**{**request, "allow_cloud": False}, confirmed=True)
    assert missing_cloud.value.code == "GUI_CORRECTION_CLOUD_OPT_IN_REQUIRED"


def test_gui_correction_preflight_rejects_missing_cloud_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    provider = SimpleNamespace(
        provider_id="openrouter",
        endpoint_identity="https://openrouter.ai/api/v1",
        model_id="google/gemini-2.5-flash",
    )

    with pytest.raises(GuiCorrectionError) as missing:
        _preflight_provider(provider, ApplicationConfig())

    assert missing.value.code == "GUI_CORRECTION_CREDENTIAL_MISSING"


def test_gui_correction_derives_project_id_from_dictionary(tmp_path: Path) -> None:
    result = tmp_path / EXAMPLE.name
    result.write_bytes(EXAMPLE.read_bytes())
    source_dictionary = (
        ROOT / "dictionaries/ethics-in-the-loop/correction/pl/ethics-in-the-loop-pl-v1.json"
    )
    dictionary = tmp_path / source_dictionary.name
    dictionary.write_bytes(source_dictionary.read_bytes())

    outcome = controller(tmp_path).generate(
        result=str(result),
        output_directory=str(tmp_path / "candidates"),
        resume_directory=str(tmp_path / "state"),
        provider_name="openrouter",
        model="google/gemini-2.5-flash",
        endpoint="https://openrouter.ai/api/v1",
        allow_remote_endpoint=False,
        allow_cloud=True,
        reasoning_max_tokens=0,
        dictionary_path=str(dictionary),
        project_id="",
        confirmed=True,
    )

    assert outcome["dictionary"]["project_id"] == "ethics-in-the-loop"
