# Run Phase 9 long-duration and endurance validation

This gate exercises the production accurate preset on realistic Polish podcast material.
It measures operational stability rather than lexical accuracy: these four files do not
yet have manually verified references. Run the cases in order and stop after a failure.
Each case has an independent output directory and can be resumed without repeating
earlier successful work.

The input recordings and generated transcripts are external test data. Do not commit
them to the application repository.

## 0. Update the application and create the external sandbox

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_P9_LONG_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase9-long-XXXXXXXX)"
export EWP_P9_LONG_OUTPUT="$EWP_P9_LONG_ROOT/output"
export EWP_P9_LONG_EVIDENCE="$EWP_P9_LONG_ROOT/evidence"
export EWP_P9_LONG_CONFIG="$EWP_P9_LONG_ROOT/transcriber.toml"
mkdir -p "$EWP_P9_LONG_OUTPUT" "$EWP_P9_LONG_EVIDENCE"
printf '[runtime]\nwork_root = "%s"\n' "$EWP_P9_LONG_ROOT/work" \
    > "$EWP_P9_LONG_CONFIG"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
printf 'sandbox=%s\n' "$EWP_P9_LONG_ROOT"
```

The log must contain commit `3ee0347` or later. At that commit, 231 tests should pass.

## 1. Verify immutable inputs and media properties

```bash
export EWP_P901="$EWP_TESTDATA/audio/p9-01-long-single-polish.wav"
export EWP_P902="$EWP_TESTDATA/audio/p9-02-long-two-speakers-polish.mp3"
export EWP_P903="$EWP_TESTDATA/audio/p9-03-long-two-speakers-polish.mp3"
export EWP_P904="$EWP_TESTDATA/audio/p9-04-endurance-two-speakers-polish.mp3"

for path in "$EWP_P901" "$EWP_P902" "$EWP_P903" "$EWP_P904"; do
    test -s "$path" && echo "present: $(basename "$path")"
    ffprobe -v error -select_streams a:0 \
        -show_entries stream=codec_name,sample_rate,channels \
        -show_entries format=duration -of default=noprint_wrappers=1 "$path"
done

sha256sum "$EWP_P901" "$EWP_P902" "$EWP_P903" "$EWP_P904"
```

Accepted hashes and intended cases:

```text
1410be4e07683079de812481ac1829d01d29e0aab185b656d0f2f989c8d34708  p9-01-long-single-polish.wav
65c25d859864720bef791cf740d0d41caac3411d38d4c4145a9cefc651823030  p9-02-long-two-speakers-polish.mp3
8039ac3b9b9e09491639dea73eae5a6f70f3beebaeb042a304666ed9606d9869  p9-03-long-two-speakers-polish.mp3
35ac2e07454a03d08cf8631219a6aa99454eb3442d2f83db52008dba606db267  p9-04-endurance-two-speakers-polish.mp3
```

- P9-01: about 21.5 minutes, mono, one speaker, deliberately long silent periods;
- P9-02: about 34.5 minutes, dual mono, two speakers, no overlap;
- P9-03: about 50 minutes, dual mono, two speakers, no overlap;
- P9-04: about 151 minutes, mono, two speakers, six concatenated episodes with short
  silent boundaries and no overlap.

Stop if any hash differs.

## 2. Inspect all inputs without loading models

```bash
for path in "$EWP_P901" "$EWP_P902" "$EWP_P903" "$EWP_P904"; do
    stem="$(basename "${path%.*}")"
    uv run --locked transcriber inspect "$path" --json-output \
        > "$EWP_P9_LONG_EVIDENCE/$stem.inspect.json"
done

uv run --locked python - "$EWP_P9_LONG_EVIDENCE" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
expected = {
    "p9-01-long-single-polish": "mono",
    "p9-02-long-two-speakers-polish": "dual-mono",
    "p9-03-long-two-speakers-polish": "dual-mono",
    "p9-04-endurance-two-speakers-polish": "mono",
}
for stem, mode in expected.items():
    report = json.loads((root / f"{stem}.inspect.json").read_text(encoding="utf-8"))
    assert len(report["episodes"]) == 1
    episode = report["episodes"][0]
    assert len(episode["sources"]) == 1
    source = episode["sources"][0]
    actual = source["channel_classification"]["processing_mode"]
    assert actual == mode, (stem, actual, mode)
    print(
        f"PASS {stem}: duration_ms={episode['duration_ms']}, "
        f"processing={actual}, warnings={len(episode['warnings'])}"
    )
PY
```

`AUDIO_HIGH_SILENCE_RATIO` is expected and informative for P9-01. Other warning codes
must be reported before transcription, but warning-only diagnostics do not block MVP
processing.

## 3. Define the measured offline runner

The helper records wall-clock/resource statistics and one-second GPU samples. It stops
the monitor even when transcription fails and returns the transcription exit code.

```bash
run_measured() {
    case_id="$1"
    speaker_count="$2"
    input_path="$3"
    case_output="$EWP_P9_LONG_OUTPUT/$case_id"
    mkdir -p "$case_output"

    nvidia-smi \
        --query-gpu=timestamp,name,utilization.gpu,memory.used,memory.total \
        --format=csv,noheader,nounits --loop=1 \
        > "$EWP_P9_LONG_EVIDENCE/$case_id.gpu.csv" &
    monitor_pid=$!

    set +e
    /usr/bin/time -v -o "$EWP_P9_LONG_EVIDENCE/$case_id.time.txt" \
        env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
        uv run --locked transcriber transcribe "$input_path" \
        --config "$EWP_P9_LONG_CONFIG" \
        --speaker-count "$speaker_count" \
        --output-dir "$case_output" \
        --non-interactive \
        > "$EWP_P9_LONG_EVIDENCE/$case_id.stdout.txt" \
        2> "$EWP_P9_LONG_EVIDENCE/$case_id.stderr.txt"
    command_exit=$?
    kill "$monitor_pid" 2>/dev/null
    wait "$monitor_pid" 2>/dev/null
    set -e

    printf '%s\n' "$command_exit" > "$EWP_P9_LONG_EVIDENCE/$case_id.exit.txt"
    printf '%s exit=%s\n' "$case_id" "$command_exit"
    return "$command_exit"
}
```

Defining the function produces no terminal output. Output begins when `run_measured` is
called in the following sections; the shell's `[1] PID` line identifies the temporary
background GPU monitor.

The local model snapshots must already be installed. `HF_TOKEN` remains absent, and
both offline environment variables remain set for every measured run.

## 4. Run the long-silence single-speaker gate

```bash
run_measured P9-01 1 "$EWP_P901"
cat "$EWP_P9_LONG_EVIDENCE/P9-01.stdout.txt"
cat "$EWP_P9_LONG_EVIDENCE/P9-01.stderr.txt"
```

Exit code must be zero. Model warnings already accepted in earlier gates may appear;
network access, CUDA OOM, traceback, failure state, or transcript hallucinations during
long silent regions fail this gate.

## 5. Run the ordinary two-speaker long-form gates

Run P9-02 first. Continue to P9-03 only after P9-02 validates successfully.

```bash
run_measured P9-02 2 "$EWP_P902"
cat "$EWP_P9_LONG_EVIDENCE/P9-02.stdout.txt"
cat "$EWP_P9_LONG_EVIDENCE/P9-02.stderr.txt"

run_measured P9-03 2 "$EWP_P903"
cat "$EWP_P9_LONG_EVIDENCE/P9-03.stdout.txt"
cat "$EWP_P9_LONG_EVIDENCE/P9-03.stderr.txt"
```

Both commands must exit zero and identify two speakers. These recordings contain no
intentional overlap, so widespread overlap flags or rapid implausible speaker switching
must be noted for manual review.

## 6. Run the 151-minute endurance gate

Run this only after P9-01 through P9-03 pass.

```bash
run_measured P9-04 2 "$EWP_P904"
cat "$EWP_P9_LONG_EVIDENCE/P9-04.stdout.txt"
cat "$EWP_P9_LONG_EVIDENCE/P9-04.stderr.txt"
```

The command must exit zero without unbounded memory growth, CUDA OOM, corrupt output,
or false speech spanning the silent episode boundaries.

## 7. Validate canonical results, exports, and resource evidence

```bash
uv run --locked python - "$EWP_P9_LONG_OUTPUT" "$EWP_P9_LONG_EVIDENCE" <<'PY'
import csv
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

output_root = Path(sys.argv[1])
evidence_root = Path(sys.argv[2])
schema = json.loads(Path("schemas/results.schema.json").read_text(encoding="utf-8"))
validator = Draft202012Validator(schema)
expected_speakers = {"P9-01": 1, "P9-02": 2, "P9-03": 2, "P9-04": 2}

for case_id, speaker_count in expected_speakers.items():
    case_output = output_root / case_id
    results = list(case_output.glob("*_results.json"))
    assert len(results) == 1, (case_id, results)
    result = json.loads(results[0].read_text(encoding="utf-8"))
    validator.validate(result)
    assert result["status"] == "completed"
    assert len(result["speakers"]) == speaker_count
    assert result["transcript"]["segments"]
    word_count = sum(len(segment["words"]) for segment in result["transcript"]["segments"])
    assert word_count > 0
    for suffix in ("_transcript.txt", "_subtitles.srt", "_subtitles.vtt"):
        matches = list(case_output.glob(f"*{suffix}"))
        assert len(matches) == 1 and matches[0].stat().st_size > 0, (case_id, suffix)

    with (evidence_root / f"{case_id}.gpu.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.reader(handle))
    used_mib = [int(row[3].strip()) for row in rows if len(row) == 5]
    assert used_mib
    assert (evidence_root / f"{case_id}.time.txt").stat().st_size > 0
    assert (evidence_root / f"{case_id}.exit.txt").read_text().strip() == "0"
    print(
        f"PASS {case_id}: speakers={len(result['speakers'])}, "
        f"segments={len(result['transcript']['segments'])}, "
        f"words={word_count}, "
        f"sampled_peak_vram_mib={max(used_mib)}"
    )
PY

for case_id in P9-01 P9-02 P9-03 P9-04; do
    grep -E 'Elapsed \(wall clock\)|Maximum resident set size' \
        "$EWP_P9_LONG_EVIDENCE/$case_id.time.txt"
done
```

## 8. Verify duplicate replay and workspace cleanup

```bash
for item in \
    "P9-01|1|$EWP_P901" \
    "P9-02|2|$EWP_P902" \
    "P9-03|2|$EWP_P903" \
    "P9-04|2|$EWP_P904"
do
    IFS='|' read -r case_id speaker_count input_path <<< "$item"
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
        uv run --locked transcriber transcribe "$input_path" \
        --config "$EWP_P9_LONG_CONFIG" \
        --speaker-count "$speaker_count" \
        --output-dir "$EWP_P9_LONG_OUTPUT/$case_id" \
        --non-interactive
done

test -z "$(find "$EWP_P9_LONG_ROOT/work" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "long-duration workdir cleanup: PASS"
sha256sum "$EWP_P9_LONG_OUTPUT"/*/*_results.json
sha256sum "$EWP_P9_LONG_EVIDENCE"/*.inspect.json
git status --short
```

Every replay must report `SKIP` without model-loading logs. No job workspace may remain,
and repository status must be empty.

## 9. Manual review and evidence to return

Review locally without sending full transcripts. Return:

- Step 0 test count, token check, and initial GPU line;
- four ffprobe summaries and accepted hashes;
- inspection PASS lines and warning codes;
- each run's exit code, stdout summary, accepted stderr warnings, elapsed wall time,
  maximum resident set size, and sampled peak VRAM;
- canonical PASS lines, result hashes, duplicate summaries, and cleanup PASS;
- concise observations for P9-01 silent regions, P9-02/P9-03 speaker stability, and
  P9-04 episode boundaries;
- empty repository status.

Do not send audio, transcripts, GPU sample files, full canonical JSON, model paths,
tokens, or transcript-derived text.
