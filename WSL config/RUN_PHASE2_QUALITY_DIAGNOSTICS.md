# Run the Phase 2 quality-diagnostics gate

This gate generates four small deterministic PCM fixtures outside the repository and
validates every warning through the production `transcriber inspect` command. The files
are mechanics fixtures only; they do not represent speech-quality benchmarks.

## 0. Update and set paths

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_QUALITY_FIXTURES="$HOME/transkrypcje/ewp-transcripts-testdata/phase0/quality-fixtures"
export EWP_QUALITY_REPORT="$EWP_QUALITY_FIXTURES/quality-inspection.json"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check
```

The log must contain commit `bc5869a` or a later commit that includes it. At that commit,
WSL is expected to report 75 passing tests. The authoritative criterion is zero failures
and no skipped FFmpeg integration test.

## 1. Generate deterministic WAV fixtures

```bash
mkdir -p "$EWP_QUALITY_FIXTURES"

uv run --locked python - "$EWP_QUALITY_FIXTURES" <<'PY'
import math
import struct
import sys
import wave
from pathlib import Path

root = Path(sys.argv[1])
rate = 16_000
frames = 2 * rate

def write(name, sample):
    with wave.open(str(root / name), "wb") as target:
        target.setnchannels(2)
        target.setsampwidth(2)
        target.setframerate(rate)
        for index in range(frames):
            left, right = sample(index)
            target.writeframesraw(struct.pack("<hh", left, right))

def tone(index, amplitude=10_000):
    return round(amplitude * math.sin(2 * math.pi * 440 * index / rate))

write("q2-01-clipping.wav", lambda i: (32767 if i % 2 else -32768,) * 2)
write("q2-02-low-level.wav", lambda i: (tone(i, 300),) * 2)
write("q2-03-imbalance.wav", lambda i: (tone(i, 10_000), tone(i, 1_000)))
write(
    "q2-04-high-silence.wav",
    lambda i: ((tone(i),) * 2) if i < rate // 2 else (0, 0),
)
PY

sha256sum "$EWP_QUALITY_FIXTURES"/*.wav
```

## 2. Run production inspection

```bash
uv run --locked transcriber inspect \
    "$EWP_QUALITY_FIXTURES" \
    --json-output \
    > "$EWP_QUALITY_REPORT"

test -s "$EWP_QUALITY_REPORT" && echo "quality report: present"
```

## 3. Verify warning codes and raw measurements

```bash
uv run --locked python - "$EWP_QUALITY_REPORT" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = {
    "q2-01-clipping": "AUDIO_CLIPPING",
    "q2-02-low-level": "AUDIO_LOW_LEVEL",
    "q2-03-imbalance": "AUDIO_CHANNEL_IMBALANCE",
    "q2-04-high-silence": "AUDIO_HIGH_SILENCE_RATIO",
}

episodes = {episode["job_id"]: episode for episode in report["episodes"]}
assert set(episodes) == set(expected), sorted(episodes)
for job_id, warning_code in expected.items():
    episode = episodes[job_id]
    codes = {warning["code"] for warning in episode["warnings"]}
    assert warning_code in codes, (job_id, sorted(codes))
    metrics = episode["sources"][0]["channel_metrics"]
    assert metrics is not None, job_id
    print(f"PASS {job_id}: {warning_code}")
PY
```

Additional warnings are acceptable when a deliberately pathological fixture crosses more
than one threshold. Every named warning must be present.

## 4. Verify human-readable warning output

```bash
uv run --locked transcriber inspect "$EWP_QUALITY_FIXTURES/q2-01-clipping.wav"
```

The output must contain `WARNING AUDIO_CLIPPING` and must still complete successfully.
Warnings are non-fatal and never trigger audio modification.

## 5. Confirm source files were not modified

```bash
sha256sum "$EWP_QUALITY_FIXTURES"/*.wav
sha256sum "$EWP_QUALITY_REPORT"
git status --short
```

Compare the WAV hashes with section 1. They must be identical. The repository worktree
must remain clean except for the owner's intentionally untracked `LICENSE_SKETCH.TXT`, if
present.

Send back the test summary, four `PASS` lines, human clipping report, both sets of WAV
hashes, report hash, and any unexpected warning or error.
