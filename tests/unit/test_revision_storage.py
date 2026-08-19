"""Tests for collision-safe immutable revision publication."""

import json
import multiprocessing
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from ewp_transcripts.domain.errors import UnsafeOutputNameError
from ewp_transcripts.domain.revision import TranscriptRevision, load_transcript_revision
from ewp_transcripts.revision_storage import publish_next_revision, revision_filename

ROOT = Path(__file__).resolve().parents[2]
REVISION_EXAMPLE = ROOT / "examples/revision.example.json"
REVISION_SCHEMA = ROOT / "schemas/revision.schema.json"


def _revision() -> TranscriptRevision:
    return TranscriptRevision.model_validate_json(REVISION_EXAMPLE.read_text(encoding="utf-8"))


def _publish_after_start(
    output_directory: Path,
    start: Any,
    results: Any,
) -> None:
    start.wait()
    allocated, path = publish_next_revision(
        _revision(),
        output_directory=output_directory,
        lock_timeout_seconds=5,
    )
    results.put((allocated.revision_number, path.name))


def test_revision_filename_distinguishes_base_result_versions() -> None:
    assert (
        revision_filename(job_id="episode", result_version=1, revision_number=1)
        == "episode_revision_001.json"
    )
    assert (
        revision_filename(job_id="episode", result_version=2, revision_number=12)
        == "episode_v002_revision_012.json"
    )


def test_revision_filename_rejects_unsafe_job_id() -> None:
    with pytest.raises(UnsafeOutputNameError):
        revision_filename(job_id="../episode", result_version=1, revision_number=1)


def test_publication_allocates_versions_without_overwriting(tmp_path: Path) -> None:
    original = _revision()

    first, first_path = publish_next_revision(original, output_directory=tmp_path)
    second, second_path = publish_next_revision(original, output_directory=tmp_path)

    assert first.revision_number == 1
    assert second.revision_number == 2
    assert first_path.name == "revision-example_revision_001.json"
    assert second_path.name == "revision-example_revision_002.json"
    assert first_path.read_bytes() != b""
    assert load_transcript_revision(first_path) == first
    assert load_transcript_revision(second_path) == second


def test_concurrent_publication_allocates_distinct_revision_numbers(tmp_path: Path) -> None:
    context = multiprocessing.get_context("fork")
    start = context.Event()
    results = context.Queue()
    processes = [
        context.Process(target=_publish_after_start, args=(tmp_path, start, results))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    start.set()
    for process in processes:
        process.join(timeout=10)

    assert [process.exitcode for process in processes] == [0, 0]
    allocations = sorted(results.get(timeout=1) for _ in processes)
    assert allocations == [
        (1, "revision-example_revision_001.json"),
        (2, "revision-example_revision_002.json"),
    ]


def test_publication_uses_result_version_in_filename(tmp_path: Path) -> None:
    data = json.loads(REVISION_EXAMPLE.read_text(encoding="utf-8"))
    data["base_result"]["result_version"] = 2
    revision = TranscriptRevision.model_validate_json(json.dumps(data))

    allocated, path = publish_next_revision(revision, output_directory=tmp_path)

    assert allocated.revision_number == 1
    assert path.name == "revision-example_v002_revision_001.json"


def test_published_revision_satisfies_json_schema(tmp_path: Path) -> None:
    _, path = publish_next_revision(_revision(), output_directory=tmp_path)
    schema = json.loads(REVISION_SCHEMA.read_text(encoding="utf-8"))
    artifact = json.loads(path.read_text(encoding="utf-8"))

    errors = Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    ).iter_errors(artifact)
    assert list(errors) == []
