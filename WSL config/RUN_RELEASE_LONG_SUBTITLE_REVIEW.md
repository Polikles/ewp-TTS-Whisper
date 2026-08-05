# Review long-form subtitles in a local player

This supplementary gate checks whether the accepted subtitle rules remain aesthetically
stable across a representative podcast episode. It uses the previously completed P9-02
canonical result: approximately 34.7 minutes, two speakers, dual mono, and no overlap.
It does not rerun ASR, alignment, or diarization.

## 0. Synchronize and locate the canonical result

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check

export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_LONG_SUB_AUDIO="$EWP_TESTDATA/audio/p9-02-long-two-speakers-polish.mp3"
export EWP_LONG_SUB_RESULT="$EWP_TESTDATA/phase9-long-gGsPOpsQ/output/P9-02/p9-02-long-two-speakers-polish_results.json"
export EWP_LONG_SUB_ROOT="$(mktemp -d "$EWP_TESTDATA/release-long-subtitles-XXXXXXXX")"
export EWP_LONG_SUB_OUTPUT="$EWP_LONG_SUB_ROOT/output"
mkdir -p "$EWP_LONG_SUB_OUTPUT"

test -s "$EWP_LONG_SUB_AUDIO" && echo "P9-02 audio: present"
test -s "$EWP_LONG_SUB_RESULT" && echo "P9-02 canonical result: present"
printf 'sandbox=%s\n' "$EWP_LONG_SUB_ROOT"
```

Expected commit: `17f5d86` or later and 270 passing tests. If the canonical result is
absent, stop and report it; do not rerun the GPU pipeline merely to continue this gate.

## 1. Export current SRT and WebVTT without models

```bash
CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber export "$EWP_LONG_SUB_RESULT" \
    --output-dir "$EWP_LONG_SUB_OUTPUT" \
    --format srt --format vtt

export EWP_LONG_SUB_SRT="$EWP_LONG_SUB_OUTPUT/p9-02-long-two-speakers-polish_subtitles.srt"
export EWP_LONG_SUB_VTT="$EWP_LONG_SUB_OUTPUT/p9-02-long-two-speakers-polish_subtitles.vtt"
test -s "$EWP_LONG_SUB_SRT" && echo "long SRT: present"
test -s "$EWP_LONG_SUB_VTT" && echo "long VTT: present"
sha256sum "$EWP_LONG_SUB_RESULT" "$EWP_LONG_SUB_SRT" "$EWP_LONG_SUB_VTT"
```

## 2. Full SRT review

Open P9-02 audio with the SRT in a local player that supports external subtitles. Review
the complete episode at normal speed. The exact player is not normative; record its name
and version.

Check:

- synchronization at the beginning, around every five minutes, and at the end;
- every speaker transition encountered during normal playback;
- no one-word or unreadably brief cues;
- no avoidable one-line cue in the middle of a continuous speaker turn;
- one-line cues at turn endings or silence-separated short statements remain natural;
- no protected Polish word is stranded at a visible line ending when a readable split
  exists;
- occasional 47–50-character lines remain comfortable;
- pauses, sentence endings, and cue changes feel natural;
- no accidental overlap, missing subtitle region, or subtitle lingering into unrelated
  speech or silence.

## 3. Text scan and WebVTT spot-check

Read the complete SRT once without playback to catch layout patterns that are easy to
miss in real time. Then load WebVTT in a compatible player or browser and spot-check at
least the beginning, middle, end, and three speaker transitions. SRT and WebVTT share cue
generation, so a second complete playback is unnecessary unless their behavior differs.

Record PASS/FAIL for:

```text
[ ] complete SRT playback is readable and synchronized
[ ] complete SRT text scan finds no systematic layout defect
[ ] WebVTT spot-check matches SRT text and timing
[ ] speaker labels remain stable across the episode
[ ] 42–50 character policy remains comfortable
[ ] nonfinal one-line rule behaves as documented
```

## 4. Evidence

```bash
git status --short
```

Send the player name/version, completed checklist, three hashes, and any failing cue with
its preceding and following cue. Generated review files remain outside Git. Do not copy
or commit `LICENSE_SKETCH.TXT`.
