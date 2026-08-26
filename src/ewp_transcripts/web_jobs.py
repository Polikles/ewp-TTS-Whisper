"""Single-worker transcription queue for the local browser GUI."""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from queue import Queue
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from ewp_transcripts.application import transcribe_one
from ewp_transcripts.config import ApplicationConfig
from ewp_transcripts.domain.errors import ApplicationError


class GuiTranscriptionJob(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    input_path: str
    output_directory: str
    created_at: datetime
    updated_at: datetime
    result_path: str | None = None
    error: dict[str, str] | None = None


TranscriptionService = Callable[..., Any]


class GuiTranscriptionQueue:
    """Run at most one GPU-intensive transcription at a time."""

    def __init__(
        self,
        *,
        config: ApplicationConfig,
        service: TranscriptionService = transcribe_one,
    ) -> None:
        self._config = config
        self._service = service
        self._pending: Queue[tuple[str, Path, Path] | None] = Queue()
        self._jobs: dict[str, GuiTranscriptionJob] = {}
        self._order: deque[str] = deque(maxlen=50)
        self._lock = threading.Lock()
        self._worker = threading.Thread(
            target=self._run,
            name="ewp-gui-transcription",
            daemon=False,
        )
        self._worker.start()

    def submit(self, input_path: Path, output_directory: Path) -> GuiTranscriptionJob:
        now = datetime.now(UTC)
        job = GuiTranscriptionJob(
            job_id=str(uuid4()),
            status="queued",
            input_path=str(input_path),
            output_directory=str(output_directory),
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[job.job_id] = job
            self._order.appendleft(job.job_id)
        self._pending.put((job.job_id, input_path, output_directory))
        return job

    def jobs(self) -> tuple[GuiTranscriptionJob, ...]:
        with self._lock:
            return tuple(self._jobs[job_id] for job_id in self._order)

    def close(self) -> None:
        self._pending.put(None)
        self._worker.join()

    def _replace(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            self._jobs[job_id] = self._jobs[job_id].model_copy(
                update={**updates, "updated_at": datetime.now(UTC)}
            )

    def _run(self) -> None:
        while True:
            item = self._pending.get()
            if item is None:
                return
            job_id, input_path, output_directory = item
            self._replace(job_id, status="running")
            try:
                outcome = self._service(
                    input_path,
                    config=self._config,
                    output_directory=output_directory,
                )
                self._replace(
                    job_id,
                    status="completed",
                    result_path=str(outcome.result_path) if outcome.result_path else None,
                )
            except ApplicationError as error:
                self._replace(
                    job_id,
                    status="failed",
                    error={"code": error.code, "message": str(error)},
                )
            except Exception:
                self._replace(
                    job_id,
                    status="failed",
                    error={
                        "code": "GUI_TRANSCRIPTION_FAILED",
                        "message": "Transcription failed unexpectedly; inspect retained job state.",
                    },
                )
