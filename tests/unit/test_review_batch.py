"""Tests for deterministic isolated batch review preparation."""

import json
from pathlib import Path

from ewp_transcripts.application import prepare_review_batch
from ewp_transcripts.config import ApplicationConfig, RuntimeConfig
from ewp_transcripts.review_discovery import discover_review_files, discover_review_results

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/results.example.json"


def _result(path: Path, job_id: str) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["job_id"] = job_id
    data["episode"]["episode_id"] = job_id
    path.write_text(json.dumps(data), encoding="utf-8")


def _config(tmp_path: Path, *, continue_after_error: bool = True) -> ApplicationConfig:
    return ApplicationConfig(
        runtime=RuntimeConfig(
            work_root=tmp_path / "work",
            continue_batch_after_error=continue_after_error,
        )
    )


def test_result_discovery_is_natural_nonrecursive_and_ignores_unrelated_files(
    tmp_path: Path,
) -> None:
    _result(tmp_path / "episode10_results.json", "episode10")
    _result(tmp_path / "episode2_results.json", "episode2")
    (tmp_path / "notes.json").write_text("{}", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    _result(nested / "episode3_results.json", "episode3")

    direct = discover_review_results(tmp_path)
    recursive = discover_review_results(tmp_path, recursive=True)

    assert [path.name for path in direct] == ["episode2_results.json", "episode10_results.json"]
    assert [path.name for path in recursive] == [
        "episode2_results.json",
        "episode3_results.json",
        "episode10_results.json",
    ]


def test_batch_continues_after_invalid_result_and_summarizes(tmp_path: Path) -> None:
    source = tmp_path / "results"
    source.mkdir()
    _result(source / "episode2_results.json", "episode2")
    (source / "episode3_results.json").write_text("invalid", encoding="utf-8")
    _result(source / "episode10_results.json", "episode10")

    outcome = prepare_review_batch(source, config=_config(tmp_path))

    assert [job.result_path.name for job in outcome.jobs] == [
        "episode2_results.json",
        "episode3_results.json",
        "episode10_results.json",
    ]
    assert [job.status for job in outcome.jobs] == ["prepared", "failed", "prepared"]
    assert outcome.prepared == 2
    assert outcome.failed == 1
    assert outcome.stopped_early is False
    assert outcome.jobs[1].failure_code == "REVISION_BASE_HASH_MISMATCH"
    assert outcome.jobs[1].failure_message is not None
    assert outcome.output_directory == source / "review-ewp-transcripts"


def test_batch_stop_policy_leaves_later_results_unstarted(tmp_path: Path) -> None:
    source = tmp_path / "results"
    source.mkdir()
    (source / "episode2_results.json").write_text("invalid", encoding="utf-8")
    _result(source / "episode10_results.json", "episode10")

    outcome = prepare_review_batch(
        source,
        config=_config(tmp_path, continue_after_error=False),
    )

    assert [job.result_path.name for job in outcome.jobs] == ["episode2_results.json"]
    assert outcome.stopped_early is True
    assert not (outcome.output_directory / "episode10.review.txt").exists()


def test_review_file_discovery_is_natural_and_filters_unrelated(tmp_path: Path) -> None:
    for name in ("episode10.review.txt", "episode2.review.txt", "notes.txt"):
        (tmp_path / name).write_text("review", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "episode3.review_v002.txt").write_text("review", encoding="utf-8")

    assert [path.name for path in discover_review_files(tmp_path)] == [
        "episode2.review.txt",
        "episode10.review.txt",
    ]
    assert [path.name for path in discover_review_files(tmp_path, recursive=True)] == [
        "episode2.review.txt",
        "episode3.review_v002.txt",
        "episode10.review.txt",
    ]
