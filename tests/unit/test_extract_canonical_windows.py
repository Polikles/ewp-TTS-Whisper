"""Tests for focused canonical timeline diagnostics."""

import importlib.util
from pathlib import Path

TOOL_PATH = Path(__file__).resolve().parents[2] / "tools" / "extract_canonical_windows.py"
SPEC = importlib.util.spec_from_file_location("extract_canonical_windows", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
extract_windows = MODULE.extract_windows


def test_extracts_only_segments_intersecting_each_requested_window() -> None:
    payload = {
        "transcript": {
            "segments": [
                {"start_ms": 100, "end_ms": 200, "text": "first"},
                {"start_ms": 250, "end_ms": 400, "text": "second"},
            ]
        }
    }

    report = extract_windows(payload, [(0, 150), (200, 300), (500, 600)])

    assert [[segment["text"] for segment in item["segments"]] for item in report] == [
        ["first"],
        ["second"],
        [],
    ]
