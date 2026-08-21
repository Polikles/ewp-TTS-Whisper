"""End-to-end secret and payload-boundary checks for correction artifacts."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ewp_transcripts.application import apply_correction, audit_revision_file
from ewp_transcripts.config import (
    ApplicationConfig,
    CorrectionConfig,
    GeneralConfig,
    RuntimeConfig,
)
from ewp_transcripts.correction_benchmark import (
    build_correction_benchmark_bundle,
    evaluate_correction_benchmark,
    load_correction_benchmark_manifest,
)
from ewp_transcripts.openrouter_adapter import (
    OpenRouterAdapterConfig,
    OpenRouterCorrectionProvider,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def test_cloud_correction_artifacts_do_not_leak_secret_or_public_payloads(
    tmp_path: Path,
) -> None:
    secret = "credential-that-must-never-be-persisted"
    base = tmp_path / "base" / "base_results.json"
    base.parent.mkdir()
    base.write_bytes(EXAMPLE.read_bytes())
    captured_headers: list[dict[str, str]] = []

    def transport(
        url: str, headers: Mapping[str, str], payload: bytes, timeout: float
    ) -> dict[str, Any]:
        del url, timeout
        captured_headers.append(dict(headers))
        request = json.loads(payload)["messages"][1]["content"]
        task = json.loads(request)
        response = {
            "operation_id": task["operation_id"],
            "speaker_blocks": [
                {
                    "speaker_id": block["speaker_id"],
                    "corrected_text": block["text"],
                }
                for block in task["editable_speaker_blocks"]
            ],
        }
        return {"choices": [{"message": {"content": json.dumps(response)}}]}

    provider = OpenRouterCorrectionProvider(
        OpenRouterAdapterConfig(model_id="privacy-test"),
        transport=transport,
        environment={"OPENROUTER_API_KEY": secret},
    )
    config = ApplicationConfig(
        general=GeneralConfig(offline=False, interactive=False),
        correction=CorrectionConfig(
            provider="openrouter",
            model="privacy-test",
            target_tokens=4,
            max_tokens=4,
            context_tokens=1,
            consent_store=tmp_path / "config" / "correction-consent.json",
        ),
        runtime=RuntimeConfig(work_root=tmp_path / "work"),
    )
    applied = apply_correction(
        base,
        config=config,
        provider=provider,
        consent_choice="accept_persistently",
        output_directory=tmp_path / "candidate",
        resume_directory=tmp_path / "resume",
    )
    audit_revision_file(
        applied.revision_path,
        config=config,
        results_directory=base.parent,
        output_directory=tmp_path / "audits",
    )

    candidate_base = tmp_path / "candidate" / base.name
    candidate_base.write_bytes(base.read_bytes())
    gold = tmp_path / "gold"
    gold.mkdir()
    (gold / base.name).write_bytes(base.read_bytes())
    gold_revision = json.loads(applied.revision_path.read_text(encoding="utf-8"))
    gold_revision["revision_number"] = 2
    (gold / "S01E01_revision_002.json").write_text(json.dumps(gold_revision), encoding="utf-8")
    manifest_path = build_correction_benchmark_bundle(
        base_directory=base.parent,
        candidate_directory=applied.revision_path.parent,
        gold_directory=gold,
        output_directory=tmp_path / "benchmark",
    )
    report = evaluate_correction_benchmark(load_correction_benchmark_manifest(manifest_path))
    report_path = tmp_path / "correction-report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert captured_headers
    assert captured_headers[0]["Authorization"] == f"Bearer {secret}"
    for artifact in tmp_path.rglob("*"):
        if artifact.is_file():
            assert secret.encode() not in artifact.read_bytes(), artifact

    public_artifacts = (
        config.correction.consent_store,
        manifest_path,
        report_path,
    )
    transcript_phrase = "Welcome to another episode"
    for artifact in public_artifacts:
        assert transcript_phrase not in artifact.read_text(encoding="utf-8"), artifact
