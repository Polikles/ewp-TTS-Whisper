#!/usr/bin/env python3
"""Measure channel similarity and activity without printing audio or transcript data."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from ewp_transcripts.media import probe_media
from ewp_transcripts.media.channel_analysis import (
    ANALYSIS_SAMPLE_RATE_HZ,
    measure_file_channels,
)

METRICS_VERSION = "ewp-phase2-channel-metrics-v1"


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _measure(path: Path) -> dict[str, object]:
    probe = probe_media(path)
    if len(probe.audio_streams) != 1:
        raise RuntimeError("Channel calibration requires exactly one audio stream")
    stream = probe.audio_streams[0]
    metrics = measure_file_channels(path)
    return {
        "file": path.name,
        "sha256": _sha256(path),
        "duration_ms": probe.duration_ms,
        "codec": stream.codec,
        "original_sample_rate_hz": stream.sample_rate_hz,
        "original_channels": stream.channels,
        "metrics": metrics.model_dump(mode="json"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure stereo channel features.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = {
        "metrics_version": METRICS_VERSION,
        "analysis_sample_rate_hz": ANALYSIS_SAMPLE_RATE_HZ,
        "files": [_measure(path.absolute()) for path in args.files],
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
