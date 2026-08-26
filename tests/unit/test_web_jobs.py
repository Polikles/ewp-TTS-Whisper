import time
from pathlib import Path
from types import SimpleNamespace

from ewp_transcripts.config import ApplicationConfig
from ewp_transcripts.web_jobs import GuiTranscriptionQueue


def wait_for_terminal(queue: GuiTranscriptionQueue, timeout: float = 1.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = queue.jobs()[0]
        if job.status in {"completed", "failed"}:
            return job
        time.sleep(0.005)
    raise AssertionError("job did not finish")


def test_queue_runs_application_service_and_records_result(tmp_path: Path) -> None:
    source = tmp_path / "episode.wav"
    output = tmp_path / "output"
    calls = []

    def transcribe(path, **kwargs):
        calls.append((path, kwargs))
        return SimpleNamespace(result_path=output / "episode_results.json")

    queue = GuiTranscriptionQueue(config=ApplicationConfig(), service=transcribe)
    try:
        submitted = queue.submit(source, output)
        completed = wait_for_terminal(queue)
    finally:
        queue.close()

    assert submitted.status == "queued"
    assert completed.status == "completed"
    assert completed.result_path == str(output / "episode_results.json")
    assert calls[0][0] == source
    assert calls[0][1]["output_directory"] == output


def test_queue_sanitizes_unexpected_failure(tmp_path: Path) -> None:
    def fail(*args, **kwargs):
        raise RuntimeError("secret backend detail")

    queue = GuiTranscriptionQueue(config=ApplicationConfig(), service=fail)
    try:
        queue.submit(tmp_path / "episode.wav", tmp_path / "output")
        failed = wait_for_terminal(queue)
    finally:
        queue.close()

    assert failed.status == "failed"
    assert failed.error is not None
    assert failed.error["code"] == "GUI_TRANSCRIPTION_FAILED"
    assert "secret" not in failed.error["message"]
