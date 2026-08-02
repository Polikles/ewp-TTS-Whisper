#!/usr/bin/env python3
"""Run the controlled Phase 0 large-v2 versus large-v3 ASR comparison."""

from __future__ import annotations

import argparse
import gc
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import time

from phase0_score_transcript import score


CASES = {
    "P0-01": {
        "audio": "audio/p0-01-single-short.wav",
        "reference": "references/p0-01-single-short.txt",
        "audio_sha256": "7c5cc9bd72bb1383ce7e33996b5573521277af7fe5f63f5687fe6768cc380c33",
        "reference_sha256": "a06bbc24b898ccbfba5845e544194d19cbe65219b4170be875ee9b6689e15dbc",
    },
    "P0-02": {
        "audio": "audio/p0-02-single-representative.wav",
        "reference": "references/p0-02-single-representative.txt",
        "audio_sha256": "32c19ea948404ed0b08d42ce8a03dbcfc4672248ca7b261550a1d4f88f61c46a",
        "reference_sha256": "c34adb93956e0c5cd04f2abb7b4172046ee9c8120ed48b82db91c54eda3b672f",
    },
    "P0-03": {
        "audio": "audio/p0-03-two-speakers-mixed-overlap.wav",
        "reference": "references/p0-03-two-speakers-mixed-overlap.txt",
        "audio_sha256": "a62e2a771f6a09732541d22834d6be8ea25a486cbd4ab1628a5e7bb9d06076ba",
        "reference_sha256": "9841dbe8eb87ca5dc19632dee9e3ab6ced95c0d6cc5f3629e4fd3c3a453b2172",
    },
}

MODELS = {
    "large-v2": "f0fe81560cb8b68660e564f55dd99207059c092e",
    "large-v3": "edaa852ec7e145841d8ffdb056a99866b5f0a478",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_inputs(data_root: Path, model_paths: dict[str, Path]) -> None:
    for case_id, case in CASES.items():
        for kind in ("audio", "reference"):
            path = data_root / case[kind]
            if not path.is_file():
                raise FileNotFoundError(f"{case_id} {kind} is missing: {path}")
            expected = case[f"{kind}_sha256"]
            actual = sha256(path)
            if actual != expected:
                raise ValueError(
                    f"{case_id} {kind} SHA-256 mismatch: expected {expected}, got {actual}"
                )

    for model_name, model_path in model_paths.items():
        if not model_path.is_dir():
            raise FileNotFoundError(f"{model_name} snapshot is missing: {model_path}")
        if model_path.name != MODELS[model_name]:
            raise ValueError(
                f"{model_name} revision mismatch: expected {MODELS[model_name]}, "
                f"got {model_path.name}"
            )


def json_default(value: object) -> object:
    if hasattr(value, "item"):
        return value.item()  # type: ignore[union-attr, no-any-return]
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pinned large-v2/large-v3 ASR and normalized WER/CER scoring."
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--large-v2", type=Path, required=True)
    parser.add_argument("--large-v3", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model_paths = {"large-v2": args.large_v2, "large-v3": args.large_v3}
    verify_inputs(args.data_root, model_paths)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Heavy imports stay inside the executable path.
    import torch
    import whisperx

    device = "cuda"
    compute_type = "float16"
    batch_size = 4
    report: dict[str, object] = {
        "comparison": "large-v2-vs-large-v3",
        "language": "pl",
        "compute_type": compute_type,
        "batch_size": batch_size,
        "vad_method": "pyannote",
        "versions": {
            "whisperx": version("whisperx"),
            "torch": version("torch"),
        },
        "models": {},
        "macro_average": {},
    }

    for model_name, snapshot in model_paths.items():
        torch.cuda.empty_cache()
        started = time.perf_counter()
        model = whisperx.load_model(
            str(snapshot),
            device,
            compute_type=compute_type,
            language="pl",
            vad_method="pyannote",
            local_files_only=True,
        )
        torch.cuda.synchronize()
        load_seconds = time.perf_counter() - started
        case_reports: dict[str, object] = {}

        for case_id, case in CASES.items():
            audio_path = args.data_root / case["audio"]
            reference_path = args.data_root / case["reference"]
            audio = whisperx.load_audio(str(audio_path))
            started = time.perf_counter()
            hypothesis = model.transcribe(
                audio,
                batch_size=batch_size,
                language="pl",
                task="transcribe",
            )
            torch.cuda.synchronize()
            asr_seconds = time.perf_counter() - started

            hypothesis_path = args.output_dir / f"{case_id.lower()}-{model_name}.json"
            hypothesis_path.write_text(
                json.dumps(
                    hypothesis,
                    ensure_ascii=False,
                    indent=2,
                    default=json_default,
                )
                + "\n",
                encoding="utf-8",
            )
            hypothesis_text = " ".join(
                segment["text"] for segment in hypothesis.get("segments", [])
            )
            lexical = score(
                reference_path.read_text(encoding="utf-8"), hypothesis_text
            )
            case_reports[case_id] = {
                "asr_seconds": round(asr_seconds, 3),
                "hypothesis_sha256": sha256(hypothesis_path),
                **lexical,
            }

        del model
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        report["models"][model_name] = {  # type: ignore[index]
            "revision": MODELS[model_name],
            "load_seconds": round(load_seconds, 3),
            "after_unload_torch_mib": round(
                torch.cuda.memory_allocated() / 1024**2, 1
            ),
            "cases": case_reports,
        }
        report["macro_average"][model_name] = {  # type: ignore[index]
            metric: round(
                sum(case_reports[case][metric] for case in CASES) / len(CASES),  # type: ignore[index, operator]
                8,
            )
            for metric in ("wer", "cer")
        }

    report_path = args.output_dir / "comparison-report.json"
    serialized = json.dumps(report, indent=2) + "\n"
    report_path.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
