# Run the Phase 2 integrated inspection gate

This runbook validates the production `transcriber inspect` path on the target WSL2
workstation. It performs discovery, hashing, FFprobe inspection, streaming channel
measurement, topology classification, grouping, and compatibility checks. It does not
load ASR, alignment, diarization, or other ML models.

Run commands from the Linux filesystem, not from `/mnt/c` or `/mnt/d`. Generated reports
remain in the external test-data directory and must not be committed to the application
repository.

## 0. Set paths

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_INSPECT_EVIDENCE="$EWP_TESTDATA/evidence/phase2-inspect"

cd "$EWP_REPO"
mkdir -p "$EWP_INSPECT_EVIDENCE"
```

## 1. Update and synchronize the locked environment

The first command should show commit `bb9b63f` or a later commit containing it.

```bash
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
```

Stop if synchronization changes `uv.lock`, dependency compatibility fails, or the
required commit is absent.

## 2. Run the repository quality gate

```bash
make check
git status --short
```

Acceptance criteria:

- formatting, lint, and type checks pass;
- every test passes;
- the real FFmpeg integration test is not skipped on WSL;
- `git status --short` is empty, except for the owner's intentionally untracked
  `LICENSE_SKETCH.TXT` if it is present locally.

At commit `bb9b63f`, WSL is expected to report 69 passing tests. Treat the named
acceptance criteria as authoritative if later commits legitimately add tests.

## 3. Verify the five channel fixtures

```bash
for name in \
    p0-01-single-short.wav \
    p0-04-two-speakers-dual-mono.mp3 \
    p2-01-split-speakers.wav \
    p2-02-mixed-stereo.wav \
    p2-03-mixed-stereo.wav
do
    test -s "$EWP_TESTDATA/audio/$name" && echo "present: $name"
done
```

All five lines must report `present`. P2-02 retains its historical filename but is an
additional near-identical/dual-mono control according to measured channel content. P2-03
is the accepted mixed-stereo fixture.

## 4. Generate production JSON inspection reports

```bash
for name in \
    p0-01-single-short.wav \
    p0-04-two-speakers-dual-mono.mp3 \
    p2-01-split-speakers.wav \
    p2-02-mixed-stereo.wav \
    p2-03-mixed-stereo.wav
do
    uv run --locked transcriber inspect \
        "$EWP_TESTDATA/audio/$name" \
        --channel-mode auto \
        --json-output \
        > "$EWP_INSPECT_EVIDENCE/${name%.*}.inspect.json"
done
```

No command may download or initialize an ML model. FFmpeg and FFprobe processes are
expected because they provide media metadata and decoded channel samples.

## 5. Validate classifications, metrics, and source hashes

```bash
uv run --locked python - "$EWP_INSPECT_EVIDENCE" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
expected = {
    "p0-01-single-short": ("mono", "mono", None),
    "p0-04-two-speakers-dual-mono": ("dual-mono", "dual-mono", 2),
    "p2-01-split-speakers": ("split-speakers", "split-speakers", 2),
    "p2-02-mixed-stereo": ("dual-mono", "dual-mono", 2),
    "p2-03-mixed-stereo": ("mixed-stereo", "mixed-stereo", 2),
}

for stem, (detected, processing, channels) in expected.items():
    report = json.loads((root / f"{stem}.inspect.json").read_text(encoding="utf-8"))
    assert len(report["episodes"]) == 1, stem
    episode = report["episodes"][0]
    assert len(episode["sources"]) == 1, stem
    source = episode["sources"][0]
    decision = source["channel_classification"]
    assert decision["detected_mode"] == detected, (stem, decision)
    assert decision["processing_mode"] == processing, (stem, decision)
    assert len(source["fingerprint"]["sha256"]) == 64, stem
    if channels is None:
        assert source["stream"]["channels"] == 1, stem
        assert source["channel_metrics"] is None, stem
    else:
        assert source["stream"]["channels"] == channels, stem
        assert source["channel_metrics"] is not None, stem
    print(f"PASS {stem}: detected={detected}, processing={processing}")
PY
```

Stop if any assertion fails. Do not change classifier thresholds merely to force these
fixtures through; preserve the report and investigate the discrepancy first.

## 6. Check the human-readable report

```bash
uv run --locked transcriber inspect \
    "$EWP_TESTDATA/audio/p2-01-split-speakers.wav"
```

The report must identify one episode and show both
`detected=split-speakers` and `processing=split-speakers`.

## 7. Repeat one case with library offline controls

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --locked transcriber inspect \
    "$EWP_TESTDATA/audio/p2-03-mixed-stereo.wav" \
    --json-output \
    > "$EWP_INSPECT_EVIDENCE/p2-03-mixed-stereo.offline.inspect.json"

cmp \
    "$EWP_INSPECT_EVIDENCE/p2-03-mixed-stereo.inspect.json" \
    "$EWP_INSPECT_EVIDENCE/p2-03-mixed-stereo.offline.inspect.json" \
    && echo "offline inspection replay: identical"
```

This is a lightweight regression check that inspection does not depend on model access.
The earlier Phase 0 network-firewall gate remains the stronger proof of network isolation.

## 8. Record evidence hashes

```bash
sha256sum "$EWP_INSPECT_EVIDENCE"/*.inspect.json
```

Send back:

- the quality-gate summary;
- the five `PASS` classification lines;
- the human-readable P2-01 report;
- the offline replay result;
- all inspection-report SHA-256 lines;
- any warning or error exactly as printed.

Do not send audio, model files, tokens, or complete transcript content.
