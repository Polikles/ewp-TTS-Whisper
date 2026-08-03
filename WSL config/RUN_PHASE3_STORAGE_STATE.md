# Run the Phase 3 locking, state, and workdir gate

This gate exercises mutable storage primitives in a unique external sandbox. It does not
run transcription models or write into the repository.

## 0. Update and verify

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_PHASE3_MUTABLE_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase3-mutable-XXXXXXXX)"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check
printf 'sandbox=%s\n' "$EWP_PHASE3_MUTABLE_ROOT"
```

The log must contain commit `093f225` or later. At that commit, 122 tests should pass.

## 1. Verify cross-process lock contention and reacquisition

```bash
uv run --locked python - "$EWP_PHASE3_MUTABLE_ROOT/locked-output" <<'PY'
import subprocess
import sys
from pathlib import Path

from ewp_transcripts.output_lock import output_directory_lock

output = Path(sys.argv[1])
probe = """
import sys
from pathlib import Path
from ewp_transcripts.domain.errors import OutputLockUnavailableError
from ewp_transcripts.output_lock import output_directory_lock
try:
    with output_directory_lock(Path(sys.argv[1])):
        raise SystemExit(2)
except OutputLockUnavailableError:
    raise SystemExit(0)
"""

with output_directory_lock(output):
    child = subprocess.run([sys.executable, "-c", probe, str(output)], check=False)
    assert child.returncode == 0, child.returncode
print("PASS cross-process contention")

with output_directory_lock(output):
    pass
print("PASS lock reacquisition")
PY
```

## 2. Verify atomic reservations and terminal transition

```bash
uv run --locked python - "$EWP_PHASE3_MUTABLE_ROOT/state-output" <<'PY'
import json
import sys
from pathlib import Path
from uuid import UUID

from ewp_transcripts.config import OutputsConfig
from ewp_transcripts.domain import EpisodeInspection
from ewp_transcripts.domain.enums import JobStateStatus
from ewp_transcripts.state import reserve_job, transition_job_state

output = Path(sys.argv[1])
inspection = EpisodeInspection.model_construct(
    job_id="controlled-job",
    episode_signature_sha256="a" * 64,
    duration_ms=1000,
    sample_rate_hz=48000,
    sources=(),
    warnings=(),
)

first = reserve_job(
    inspection,
    output_directory=output,
    run_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    force=True,
    config=OutputsConfig(),
)
assert first.state and first.state.result_version == 1
assert first.state_path and first.state_path.is_file()
print("PASS running reservation v1")

second = reserve_job(
    inspection,
    output_directory=output,
    run_id=UUID("223e4567-e89b-12d3-a456-426614174000"),
    force=True,
    config=OutputsConfig(),
)
assert second.state and second.state.result_version == 2
print("PASS occupied reservation advances to v2")

failed = transition_job_state(
    first,
    status=JobStateStatus.FAILED,
    failure_code="CONTROLLED_WSL_GATE",
    failure_message="Controlled mechanics test without transcript content.",
)
assert failed.status is JobStateStatus.FAILED
assert first.state_path and not first.state_path.exists()
failed_path = output / "controlled-job_results.failed.json"
payload = json.loads(failed_path.read_text(encoding="utf-8"))
assert payload["run_id"] == "123e4567-e89b-12d3-a456-426614174000"
assert payload["failure_code"] == "CONTROLLED_WSL_GATE"
print("PASS running-to-failed transition")

assert not list(output.glob("*.tmp"))
print("PASS no temporary state files")
PY
```

## 3. Verify isolated workdir cleanup

```bash
uv run --locked python - "$EWP_PHASE3_MUTABLE_ROOT/work-root" <<'PY'
import sys
from pathlib import Path
from uuid import UUID

from ewp_transcripts.workdirs import allocate_work_directory, cleanup_work_directory

root = Path(sys.argv[1])
run_id = UUID("323e4567-e89b-12d3-a456-426614174000")
workspace = allocate_work_directory(root, run_id=run_id, job_id="controlled-job")
(workspace.path / "temporary.wav").write_bytes(b"temporary audio mechanics fixture")
sibling = root / "model-cache-must-remain"
sibling.mkdir()
(sibling / "model.bin").write_bytes(b"controlled model-like data")
print("PASS isolated workdir allocation")

cleanup_work_directory(workspace)
assert not workspace.path.exists()
assert (sibling / "model.bin").read_bytes() == b"controlled model-like data"
assert root.is_dir()
print("PASS scoped cleanup preserves sibling")
PY
```

## 4. Record artifacts and repository state

```bash
find "$EWP_PHASE3_MUTABLE_ROOT" -maxdepth 4 -type f -print | sort
find "$EWP_PHASE3_MUTABLE_ROOT" -maxdepth 4 -type f -print0 \
    | sort -z | xargs -0 sha256sum
git status --short
```

The repository status must be empty. The sandbox is intentionally retained as evidence;
it contains only controlled state, lock metadata, and model-like test bytes.

Send back the 122-test summary, all PASS lines, artifact listing and hashes, repository
status, and any unexpected warning or error.
