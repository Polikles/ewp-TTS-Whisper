# Run the Phase 4 canonical export gate

This gate validates canonical JSON ingestion plus TXT, SRT, VTT, and optional segments
exports on the target WSL installation. It uses the repository example as controlled
input, does not open source audio, and must not initialize or download ML models.

## 0. Update and prepare an external sandbox

```bash
export EWP_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_PHASE4_EXPORT_ROOT="$(mktemp -d -p "$EWP_TESTDATA" phase4-exports-XXXXXXXX)"

cd "$EWP_REPO"
git pull --ff-only
git log -1 --oneline
uv sync --locked
uv pip check
make check
cp examples/results.example.json "$EWP_PHASE4_EXPORT_ROOT/S01E01_results.json"
printf 'sandbox=%s\n' "$EWP_PHASE4_EXPORT_ROOT"
```

The log must contain commit `588080d` or later. At that commit, 150 tests should pass.
Treat the named checks as authoritative if later commits legitimately add tests.

## 1. Generate the default text and subtitle exports offline

```bash
CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber export \
    "$EWP_PHASE4_EXPORT_ROOT/S01E01_results.json"
```

Expected output:

```text
Export version: 1
WROTE .../S01E01_transcript.txt
WROTE .../S01E01_subtitles.srt
WROTE .../S01E01_subtitles.vtt
```

The command must not mention CUDA, Torch, WhisperX, pyannote, model loading, downloads,
or source-audio access.

## 2. Generate the optional segments export

```bash
CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run --locked transcriber export \
    "$EWP_PHASE4_EXPORT_ROOT/S01E01_results.json" \
    --segments
```

This invocation requests only `segments`; it must write `S01E01_segments.json` at
version 1 without modifying the canonical input.

## 3. Validate all four exports

```bash
uv run --locked python - "$EWP_PHASE4_EXPORT_ROOT" <<'PY'
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

root = Path(sys.argv[1])
repo = Path.cwd()
expected = (
    "S01E01_results.json",
    "S01E01_transcript.txt",
    "S01E01_subtitles.srt",
    "S01E01_subtitles.vtt",
    "S01E01_segments.json",
)
for name in expected:
    assert (root / name).is_file() and (root / name).stat().st_size > 0, name
    print(f"present: {name}")

txt = (root / "S01E01_transcript.txt").read_text(encoding="utf-8")
assert txt == (
    "jan:\nWelcome to another episode.\n\n"
    "anna:\nToday we discuss transcription.\n"
)
assert "-->" not in txt
print("PASS TXT layout")

srt = (root / "S01E01_subtitles.srt").read_text(encoding="utf-8")
assert re.search(r"^1\n\d{2}:\d{2}:\d{2},\d{3} --> ", srt)
assert "jan: Welcome to another episode." in srt
assert "anna: Today we discuss transcription." in srt
print("PASS SRT structure")

vtt = (root / "S01E01_subtitles.vtt").read_text(encoding="utf-8")
assert vtt.startswith("WEBVTT\n\n")
assert re.search(r"\d{2}:\d{2}:\d{2}\.\d{3} --> ", vtt)
print("PASS VTT structure")

segments = json.loads((root / "S01E01_segments.json").read_text(encoding="utf-8"))
schema = json.loads((repo / "schemas/segments.schema.json").read_text(encoding="utf-8"))
assert list(Draft202012Validator(schema).iter_errors(segments)) == []
assert segments["derived_from"]["results_file"] == "S01E01_results.json"
assert segments["segmentation"]["mode"] == "speaker_turn"
print("PASS segments schema and provenance")
PY
```

## 4. Verify skip behavior without mutation

```bash
sha256sum "$EWP_PHASE4_EXPORT_ROOT"/* > "$EWP_PHASE4_EXPORT_ROOT/hashes-before.txt"

uv run --locked transcriber export \
    "$EWP_PHASE4_EXPORT_ROOT/S01E01_results.json" \
    --format txt --format srt --format vtt --segments

sha256sum "$EWP_PHASE4_EXPORT_ROOT"/S01E01_* > "$EWP_PHASE4_EXPORT_ROOT/hashes-after.txt"
head -n 5 "$EWP_PHASE4_EXPORT_ROOT/hashes-before.txt" \
    | diff - "$EWP_PHASE4_EXPORT_ROOT/hashes-after.txt" \
    && echo "PASS existing exports unchanged"
```

The command must report four `SKIP` lines and no `WROTE` line.

## 5. Verify one coordinated forced version

```bash
uv run --locked transcriber export \
    "$EWP_PHASE4_EXPORT_ROOT/S01E01_results.json" \
    --format txt --format srt --format vtt --segments --force

for name in \
    S01E01_transcript_v002.txt \
    S01E01_subtitles_v002.srt \
    S01E01_subtitles_v002.vtt \
    S01E01_segments_v002.json
do
    test -s "$EWP_PHASE4_EXPORT_ROOT/$name" && echo "present: $name"
done
```

The command must report `Export version: 2` and four `WROTE` lines. It must not modify
the version-1 files or the canonical result.

## 6. Record evidence and repository state

```bash
sha256sum "$EWP_PHASE4_EXPORT_ROOT"/S01E01_*
find "$EWP_PHASE4_EXPORT_ROOT" -maxdepth 1 -name '.*.tmp' -print
git status --short
```

No temporary export file may remain. Repository status must be empty except for the
owner's intentionally untracked `LICENSE_SKETCH.TXT`, if present locally.

Send back:

- the quality-gate summary;
- output from the default, segments-only, repeated, and forced export commands;
- all validation `PASS` lines;
- all final SHA-256 lines;
- repository status and any unexpected warning or error.

Do not send source audio, model files, tokens, or private transcript content.
