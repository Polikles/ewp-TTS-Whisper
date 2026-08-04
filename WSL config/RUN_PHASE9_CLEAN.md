# Validate marker-safe MVP cleanup

This Phase 9 gate validates `transcriber clean all-workdirs` without audio, models, or
GPU inference. It creates controlled external workspaces through the production allocator,
ages one ownership marker, and proves that preview and confirmed cleanup preserve recent,
unknown, invalid, and model-like paths.

## 0. Update and create an external sandbox

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_P9_CLEAN_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase9-clean-XXXXXXXX)"
export EWP_P9_WORK="$EWP_P9_CLEAN_ROOT/work"
export EWP_P9_CONFIG="$EWP_P9_CLEAN_ROOT/transcriber.toml"
printf '[runtime]\nwork_root = "%s"\n' "$EWP_P9_WORK" > "$EWP_P9_CONFIG"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check
printf 'sandbox=%s\n' "$EWP_P9_CLEAN_ROOT"
```

The log must contain commit `3ea48f0` or later. At that commit, 217 tests should pass.

## 1. Create controlled eligible and preserved paths

```bash
uv run --locked python - "$EWP_P9_WORK" <<'PY'
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from ewp_transcripts.workdirs import MARKER_FILENAME, allocate_work_directory

root = Path(sys.argv[1])
old = allocate_work_directory(
    root,
    run_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    job_id="old-private-job",
)
recent = allocate_work_directory(
    root,
    run_id=UUID("223e4567-e89b-12d3-a456-426614174000"),
    job_id="recent-private-job",
)
(old.path / "private-audio.wav").write_bytes(b"old private diagnostic")
(recent.path / "private-audio.wav").write_bytes(b"recent private diagnostic")
old_time = (datetime.now(UTC) - timedelta(days=10)).timestamp()
os.utime(old.marker_path, (old_time, old_time))

model = root / "models-must-remain"
model.mkdir()
(model / "model.bin").write_bytes(b"model")
invalid = root / "323e4567-e89b-12d3-a456-426614174000" / "invalid-marker"
invalid.mkdir(parents=True)
(invalid / MARKER_FILENAME).write_text("{}", encoding="utf-8")
print(f"old={old.path}")
print(f"recent={recent.path}")
print(f"model={model / 'model.bin'}")
print(f"invalid={invalid}")
PY

find "$EWP_P9_WORK" -maxdepth 3 -type f -print | sort
sha256sum "$EWP_P9_WORK/models-must-remain/model.bin"
```

There must be two valid workspaces, one invalid-marker directory, and one model-like
sibling. All are synthetic mechanics fixtures inside the external sandbox.

## 2. Preview the age-filtered cleanup

```bash
uv run --locked transcriber clean all-workdirs \
    --config "$EWP_P9_CONFIG" --older-than 5 --dry-run

test -d "$EWP_P9_WORK/123e4567-e89b-12d3-a456-426614174000/old-private-job" \
    && echo "preview preserved old workspace: PASS"
test -d "$EWP_P9_WORK/223e4567-e89b-12d3-a456-426614174000/recent-private-job" \
    && echo "preview preserved recent workspace: PASS"
```

The command must print exactly one `WOULD REMOVE` entry for `old-private-job` and
`SUMMARY selected=1 removed=0`. Preview must not mutate either valid workspace.

## 3. Confirm the age-filtered cleanup

```bash
uv run --locked transcriber clean all-workdirs \
    --config "$EWP_P9_CONFIG" --older-than 5 --yes

test ! -e "$EWP_P9_WORK/123e4567-e89b-12d3-a456-426614174000/old-private-job" \
    && echo "old workspace removed: PASS"
test -d "$EWP_P9_WORK/223e4567-e89b-12d3-a456-426614174000/recent-private-job" \
    && echo "recent workspace preserved: PASS"
test -f "$EWP_P9_WORK/models-must-remain/model.bin" \
    && echo "model-like sibling preserved: PASS"
test -d "$EWP_P9_WORK/323e4567-e89b-12d3-a456-426614174000/invalid-marker" \
    && echo "invalid marker preserved: PASS"
sha256sum "$EWP_P9_WORK/models-must-remain/model.bin"
```

The command must print exactly one `REMOVED` entry and
`SUMMARY selected=1 removed=1`. The model hash must match section 1.

## 4. Remove the remaining valid workspace only

```bash
uv run --locked transcriber clean all-workdirs \
    --config "$EWP_P9_CONFIG" --yes

test ! -e "$EWP_P9_WORK/223e4567-e89b-12d3-a456-426614174000/recent-private-job" \
    && echo "remaining valid workspace removed: PASS"
test -f "$EWP_P9_WORK/models-must-remain/model.bin" \
    && echo "model-like sibling still preserved: PASS"
test -d "$EWP_P9_WORK/323e4567-e89b-12d3-a456-426614174000/invalid-marker" \
    && echo "invalid marker still preserved: PASS"
```

This command must select and remove only `recent-private-job`.

## 5. Record final evidence

```bash
find "$EWP_P9_WORK" -maxdepth 3 -type f -print | sort
sha256sum "$EWP_P9_WORK/models-must-remain/model.bin"
git status --short
```

Only the unknown model-like file and invalid marker fixture should remain below the work
root. Repository status must be empty. Send back the quality gate, every cleanup summary,
all PASS lines, both model hashes, final file listing, and any unexpected error.
