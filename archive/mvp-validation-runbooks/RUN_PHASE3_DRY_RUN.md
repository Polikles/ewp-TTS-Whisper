# Run the Phase 3 dry-run planning gate

This gate validates production `transcriber dry-run` behavior against a real audio file
and controlled external result metadata. Setup commands create test metadata; dry-run
itself must not create or modify any output or work directory.

## 0. Update and verify

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_DRYRUN_EVIDENCE="$EWP_TESTDATA/evidence/phase3-dry-run"
export EWP_DRYRUN_MISSING="$EWP_TESTDATA/dry-run-planned-output"
export EWP_DRYRUN_STATES="$EWP_TESTDATA/dry-run-result-states"
export EWP_DRYRUN_INPUT="$EWP_TESTDATA/audio/p0-01-single-short.wav"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check
mkdir -p "$EWP_DRYRUN_EVIDENCE" "$EWP_DRYRUN_STATES"
```

The log must contain commit `534e619` or later. At that commit, 101 tests should pass.

## 1. Plan a new job without creating its destination

Choose another unused path if this assertion fails; do not delete an existing directory.

```bash
test ! -e "$EWP_DRYRUN_MISSING" && echo "unused destination: PASS"

uv run --locked transcriber dry-run "$EWP_DRYRUN_INPUT" \
    --output-dir "$EWP_DRYRUN_MISSING" \
    --json-output \
    > "$EWP_DRYRUN_EVIDENCE/new-job.json"

test ! -e "$EWP_DRYRUN_MISSING" && echo "dry-run destination creation: PASS"
```

Validate the decision and capture the episode signature:

```bash
uv run --locked python - "$EWP_DRYRUN_EVIDENCE/new-job.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert len(report["jobs"]) == 1
job = report["jobs"][0]
assert job["decision"] == "process"
assert job["outputs"]["result_version"] == 1
assert job["outputs"]["results"].endswith("p0-01-single-short_results.json")
print(f"PASS new job: PROCESS v{job['outputs']['result_version']}")
print(job["episode_signature_sha256"])
PY
```

## 2. Create controlled completed-result metadata

This creates only minimal test metadata in the external test-data tree.

```bash
export EWP_DRYRUN_SIGNATURE="$(uv run --locked python -c \
    'import json,os; print(json.load(open(os.environ["EWP_DRYRUN_EVIDENCE"]+"/new-job.json"))["jobs"][0]["episode_signature_sha256"])')"

mkdir -p \
    "$EWP_DRYRUN_STATES/duplicate" \
    "$EWP_DRYRUN_STATES/forced" \
    "$EWP_DRYRUN_STATES/collision"

uv run --locked python - "$EWP_DRYRUN_STATES" "$EWP_DRYRUN_SIGNATURE" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
signature = sys.argv[2]

def write(directory, signature_value):
    payload = {
        "job_id": "p0-01-single-short",
        "status": "completed",
        "result_version": 1,
        "episode": {"episode_signature_sha256": signature_value},
    }
    (root / directory / "p0-01-single-short_results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

write("duplicate", signature)
write("forced", signature)
write("collision", "b" * 64)
(root / "forced" / "p0-01-single-short_results_v002.partial.json").write_text(
    "controlled occupied state\n", encoding="utf-8"
)
PY

find "$EWP_DRYRUN_STATES" -type f -print0 | sort -z | xargs -0 sha256sum \
    > "$EWP_DRYRUN_EVIDENCE/state-hashes-before.txt"
```

## 3. Validate duplicate skip

```bash
uv run --locked transcriber dry-run "$EWP_DRYRUN_INPUT" \
    --output-dir "$EWP_DRYRUN_STATES/duplicate" \
    --json-output \
    > "$EWP_DRYRUN_EVIDENCE/duplicate.json"
```

## 4. Validate forced allocation around an occupied version

Because v1 is completed and the v2 partial filename is occupied, `--force` must choose
v3.

```bash
uv run --locked transcriber dry-run "$EWP_DRYRUN_INPUT" \
    --output-dir "$EWP_DRYRUN_STATES/forced" \
    --force \
    --json-output \
    > "$EWP_DRYRUN_EVIDENCE/forced.json"
```

## 5. Validate same-name/different-signature collision

```bash
uv run --locked transcriber dry-run "$EWP_DRYRUN_INPUT" \
    --output-dir "$EWP_DRYRUN_STATES/collision" \
    --json-output \
    > "$EWP_DRYRUN_EVIDENCE/collision.json"
```

Validate all three reports:

```bash
uv run --locked python - "$EWP_DRYRUN_EVIDENCE" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])

duplicate = json.loads((root / "duplicate.json").read_text(encoding="utf-8"))["jobs"][0]
assert duplicate["decision"] == "skip"
assert duplicate["outputs"] is None
assert {w["code"] for w in duplicate["warnings"]} == {"EXISTING_RESULT_SKIPPED"}
print("PASS duplicate: SKIP")

forced = json.loads((root / "forced.json").read_text(encoding="utf-8"))["jobs"][0]
assert forced["decision"] == "process"
assert forced["outputs"]["result_version"] == 3
assert forced["outputs"]["results"].endswith("_results_v003.json")
print("PASS forced: PROCESS v3")

collision = json.loads((root / "collision.json").read_text(encoding="utf-8"))["jobs"][0]
assert collision["decision"] == "process"
assert collision["outputs"]["result_version"] == 2
assert {w["code"] for w in collision["warnings"]} == {"SOURCE_NAME_COLLISION"}
print("PASS collision: PROCESS v2 with warning")
PY
```

## 6. Prove dry-run did not modify controlled state

```bash
find "$EWP_DRYRUN_STATES" -type f -print0 | sort -z | xargs -0 sha256sum \
    > "$EWP_DRYRUN_EVIDENCE/state-hashes-after.txt"

cmp \
    "$EWP_DRYRUN_EVIDENCE/state-hashes-before.txt" \
    "$EWP_DRYRUN_EVIDENCE/state-hashes-after.txt" \
    && echo "dry-run state mutation: PASS"

test ! -e "$EWP_DRYRUN_MISSING" && echo "unused destination still absent: PASS"
```

## 7. Check human output and evidence hashes

```bash
uv run --locked transcriber dry-run "$EWP_DRYRUN_INPUT" \
    --output-dir "$EWP_DRYRUN_STATES/duplicate"

sha256sum "$EWP_DRYRUN_EVIDENCE"/*.json
git status --short
```

The human report must show `SKIP`, the existing result path, and
`WARNING EXISTING_RESULT_SKIPPED`. The repository must remain clean except for the
owner's intentionally untracked `LICENSE_SKETCH.TXT`, if present.

Send back the 101-test summary, all PASS lines, the human duplicate report, JSON hashes,
and any unexpected warning or error.
