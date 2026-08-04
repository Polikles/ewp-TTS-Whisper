# Run the initial Phase 9 lexical-quality baseline

This gate runs the production application on the three manually verified Phase 0 cases
and evaluates fresh canonical results through the manifest-driven corpus scorer. It
establishes an initial large-v2 WER/CER baseline; it is not the final release threshold
because the corpus contains only three cases.

P0-03 deliberately contains heavy overlap. Keep its deletion-heavy score visible and do
not present it as ordinary clean-speech accuracy. Plain-text references cannot measure
timestamps or diarization quality.

## 0. Update and create an external sandbox

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_P9_QUALITY_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase9-quality-XXXXXXXX)"
export EWP_P9_HYPOTHESES="$EWP_P9_QUALITY_ROOT/hypotheses"
export EWP_P9_EVIDENCE="$EWP_P9_QUALITY_ROOT/evidence"
export EWP_P9_DATASET_MANIFEST="$EWP_TESTDATA/phase9-quality-manifest.toml"
export EWP_P9_CONFIG="$EWP_P9_QUALITY_ROOT/transcriber.toml"
mkdir -p "$EWP_P9_HYPOTHESES" "$EWP_P9_EVIDENCE"
printf '[runtime]\nwork_root = "%s"\n' "$EWP_P9_QUALITY_ROOT/work" \
    > "$EWP_P9_CONFIG"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
printf 'sandbox=%s\n' "$EWP_P9_QUALITY_ROOT"
```

The log must contain commit `b10364c` or later. At that commit, 224 tests should pass.

## 1. Verify the six immutable corpus inputs

```bash
export EWP_P001_AUDIO="$EWP_TESTDATA/audio/p0-01-single-short.wav"
export EWP_P002_AUDIO="$EWP_TESTDATA/audio/p0-02-single-representative.wav"
export EWP_P003_AUDIO="$EWP_TESTDATA/audio/p0-03-two-speakers-mixed-overlap.wav"
export EWP_P001_REFERENCE="$EWP_TESTDATA/references/p0-01-single-short.txt"
export EWP_P002_REFERENCE="$EWP_TESTDATA/references/p0-02-single-representative.txt"
export EWP_P003_REFERENCE="$EWP_TESTDATA/references/p0-03-two-speakers-mixed-overlap.txt"

for path in \
    "$EWP_P001_AUDIO" "$EWP_P002_AUDIO" "$EWP_P003_AUDIO" \
    "$EWP_P001_REFERENCE" "$EWP_P002_REFERENCE" "$EWP_P003_REFERENCE"
do
    test -s "$path" && echo "present: $(basename "$path")"
done
sha256sum \
    "$EWP_P001_AUDIO" "$EWP_P001_REFERENCE" \
    "$EWP_P002_AUDIO" "$EWP_P002_REFERENCE" \
    "$EWP_P003_AUDIO" "$EWP_P003_REFERENCE"
```

Accepted hashes:

```text
7c5cc9bd72bb1383ce7e33996b5573521277af7fe5f63f5687fe6768cc380c33  p0-01-single-short.wav
a06bbc24b898ccbfba5845e544194d19cbe65219b4170be875ee9b6689e15dbc  p0-01-single-short.txt
32c19ea948404ed0b08d42ce8a03dbcfc4672248ca7b261550a1d4f88f61c46a  p0-02-single-representative.wav
c34adb93956e0c5cd04f2abb7b4172046ee9c8120ed48b82db91c54eda3b672f  p0-02-single-representative.txt
a62e2a771f6a09732541d22834d6be8ea25a486cbd4ab1628a5e7bb9d06076ba  p0-03-two-speakers-mixed-overlap.wav
9841dbe8eb87ca5dc19632dee9e3ab6ced95c0d6cc5f3629e4fd3c3a453b2172  p0-03-two-speakers-mixed-overlap.txt
```

Stop if any hash differs. These references were manually verified and contain no speaker
labels or timestamps.

## 2. Create and validate the external manifest

```bash
cat > "$EWP_P9_DATASET_MANIFEST" <<'TOML'
manifest_version = "1.0"
normalization = "ewp-phase0-lexical-v1"

[[cases]]
case_id = "P0-01"
language = "pl"
reference_path = "references/p0-01-single-short.txt"
reference_sha256 = "a06bbc24b898ccbfba5845e544194d19cbe65219b4170be875ee9b6689e15dbc"
hypothesis_path = "p0-01-single-short_results.json"
hypothesis_format = "canonical-json"

[[cases]]
case_id = "P0-02"
language = "pl"
reference_path = "references/p0-02-single-representative.txt"
reference_sha256 = "c34adb93956e0c5cd04f2abb7b4172046ee9c8120ed48b82db91c54eda3b672f"
hypothesis_path = "p0-02-single-representative_results.json"
hypothesis_format = "canonical-json"

[[cases]]
case_id = "P0-03"
language = "pl"
reference_path = "references/p0-03-two-speakers-mixed-overlap.txt"
reference_sha256 = "9841dbe8eb87ca5dc19632dee9e3ab6ced95c0d6cc5f3629e4fd3c3a453b2172"
hypothesis_path = "p0-03-two-speakers-mixed-overlap_results.json"
hypothesis_format = "canonical-json"
TOML

sha256sum "$EWP_P9_DATASET_MANIFEST"
```

The evaluator rejects parent traversal, so the manifest resides at the common external
dataset root above `references/`. It is not an application-repository file.

## 3. Generate fresh P0-01 and P0-02 canonical hypotheses offline

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P001_AUDIO" \
    --config "$EWP_P9_CONFIG" --speaker-count 1 \
    --output-dir "$EWP_P9_HYPOTHESES"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P002_AUDIO" \
    --config "$EWP_P9_CONFIG" --speaker-count 1 \
    --output-dir "$EWP_P9_HYPOTHESES"
```

Both must report `PROCESS`, `RESULT`, and three `WROTE` exports. A download, token
request, traceback, or CUDA OOM is a failure.

## 4. Generate the P0-03 exact-two-speaker hypothesis offline

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P003_AUDIO" \
    --config "$EWP_P9_CONFIG" --speaker-count 2 \
    --output-dir "$EWP_P9_HYPOTHESES"
```

This must produce a schema-valid canonical result with both anonymous speakers. Heavy
overlap may be omitted by ASR and is expected to increase deletions.

## 5. Evaluate the corpus

```bash
uv run --locked python tools/evaluate_corpus.py \
    "$EWP_P9_DATASET_MANIFEST" \
    --hypothesis-root "$EWP_P9_HYPOTHESES" \
    --output "$EWP_P9_EVIDENCE/quality-report.json" \
    --diff-output "$EWP_P9_EVIDENCE/quality-errors.diff.txt"
```

Then validate report structure without printing transcript-derived diff content:

```bash
uv run --locked python - "$EWP_P9_EVIDENCE/quality-report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["report_version"] == "ewp-corpus-quality-v1"
assert report["normalization"] == "ewp-phase0-lexical-v1"
assert report["case_count"] == 3
assert [case["case_id"] for case in report["cases"]] == ["P0-01", "P0-02", "P0-03"]
assert all(case["hypothesis_format"] == "canonical-json" for case in report["cases"])
assert sum(case["word_errors"]["reference_units"] for case in report["cases"]) == 1982
for case in report["cases"]:
    print(
        f"{case['case_id']}: WER={case['wer']:.8f}, CER={case['cer']:.8f}, "
        f"S={case['word_errors']['substitutions']}, "
        f"D={case['word_errors']['deletions']}, "
        f"I={case['word_errors']['insertions']}"
    )
macro = report["aggregate"]["macro_average"]
micro = report["aggregate"]["micro_average"]
print(f"macro: WER={macro['wer']:.8f}, CER={macro['cer']:.8f}")
print(f"micro: WER={micro['wer']:.8f}, CER={micro['cer']:.8f}")
print("lexical corpus report: PASS")
PY

test -s "$EWP_P9_EVIDENCE/quality-errors.diff.txt" \
    && echo "error-only review diff: present"
wc -l "$EWP_P9_EVIDENCE/quality-errors.diff.txt"
```

Review the diff locally, but send only concise observations about important error types,
not its transcript-derived contents.

## 6. Verify duplicate replay, cleanup, and evidence hashes

```bash
for input in "$EWP_P001_AUDIO" "$EWP_P002_AUDIO"; do
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
        uv run --locked transcriber transcribe "$input" \
        --config "$EWP_P9_CONFIG" --speaker-count 1 \
        --output-dir "$EWP_P9_HYPOTHESES"
done
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber transcribe "$EWP_P003_AUDIO" \
    --config "$EWP_P9_CONFIG" --speaker-count 2 \
    --output-dir "$EWP_P9_HYPOTHESES"

test -z "$(find "$EWP_P9_QUALITY_ROOT/work" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "quality baseline workdir cleanup: PASS"
sha256sum "$EWP_P9_HYPOTHESES"/*_results.json
sha256sum "$EWP_P9_EVIDENCE/quality-report.json" \
    "$EWP_P9_EVIDENCE/quality-errors.diff.txt"
git status --short
```

All three results and nine exports must report `SKIP` without model-loading logs.
Repository status must be empty.

Send back:

- quality gate and GPU line;
- six accepted input hashes and the final manifest hash;
- three first-run and duplicate summaries;
- per-case, macro, and micro metrics plus PASS lines;
- diff line count and concise manual observations;
- three canonical-result hashes and both report hashes;
- cleanup and repository status.

Do not send full references, hypotheses, diff content, audio, model files, or tokens.
