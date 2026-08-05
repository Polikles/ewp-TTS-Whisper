#!/usr/bin/env python3
"""Print canonical transcript segments intersecting selected timeline windows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _window(value: str) -> tuple[int, int]:
    try:
        start_text, end_text = value.split(":", maxsplit=1)
        start_ms, end_ms = int(start_text), int(end_text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("window must be START_MS:END_MS") from error
    if start_ms < 0 or end_ms <= start_ms:
        raise argparse.ArgumentTypeError("window must have 0 <= START_MS < END_MS")
    return start_ms, end_ms


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract canonical segments and words intersecting timeline windows."
    )
    parser.add_argument("result", type=Path, help="canonical result JSON")
    parser.add_argument(
        "--window",
        type=_window,
        action="append",
        required=True,
        help="half-open millisecond range START_MS:END_MS; repeatable",
    )
    return parser.parse_args()


def extract_windows(
    payload: dict[str, Any], windows: list[tuple[int, int]]
) -> list[dict[str, Any]]:
    segments = payload["transcript"]["segments"]
    return [
        {
            "window_start_ms": start_ms,
            "window_end_ms": end_ms,
            "segments": [
                segment
                for segment in segments
                if segment["start_ms"] < end_ms and start_ms < segment["end_ms"]
            ],
        }
        for start_ms, end_ms in windows
    ]


def main() -> int:
    args = parse_args()
    payload = json.loads(args.result.read_text(encoding="utf-8"))
    report = extract_windows(payload, args.window)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
