# Retest long subtitles after continuous-turn partitioning

This is an export-only text-layout retest. Do not review pacing yet.

## 0. Synchronize

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check

export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_LONG_SUB_RESULT="$EWP_TESTDATA/phase9-long-gGsPOpsQ/output/P9-02/p9-02-long-two-speakers-polish_results.json"
export EWP_LONG_SUB_OUTPUT="$EWP_TESTDATA/release-long-subtitles-wCI5Br3A/output"

test -s "$EWP_LONG_SUB_RESULT" && echo "P9-02 canonical result: present"
test -d "$EWP_LONG_SUB_OUTPUT" && echo "review output: present"
```

Expected commit: `c15ccaa` or later and 273 passing tests.

## 1. Export version 3

```bash
CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber export "$EWP_LONG_SUB_RESULT" \
    --output-dir "$EWP_LONG_SUB_OUTPUT" \
    --format srt --format vtt --force

export EWP_LONG_SUB_SRT_V3="$EWP_LONG_SUB_OUTPUT/p9-02-long-two-speakers-polish_subtitles_v003.srt"
export EWP_LONG_SUB_VTT_V3="$EWP_LONG_SUB_OUTPUT/p9-02-long-two-speakers-polish_subtitles_v003.vtt"
test -s "$EWP_LONG_SUB_SRT_V3" && echo "turn-partitioned SRT: present"
test -s "$EWP_LONG_SUB_VTT_V3" && echo "turn-partitioned VTT: present"
sha256sum "$EWP_LONG_SUB_RESULT" "$EWP_LONG_SUB_SRT_V3" "$EWP_LONG_SUB_VTT_V3"
```

## 2. Print the three regression regions

```bash
for range in '00:07:55,00:08:18' '00:25:25,00:26:10' '00:34:20,00:34:40'; do
    start=${range%,*}
    stop=${range#*,}
    awk -v start="$start" -v stop="$stop" '
        index($0, start) {show=1}
        show {print}
        show && index($0, stop) {exit}
    ' "$EWP_LONG_SUB_SRT_V3"
done
```

If a range ending does not occur as an exact cue timestamp, print a slightly wider region
manually. Verify:

- no independent `bo`, `nawet`, `błędu.`, `metody.`, or `Nie` cue;
- no timestamp overlap within the `Nie zapomnijcie…` sentence;
- no avoidable one-line cue in the middle of the continuous Alfa Fold explanation;
- every word appears exactly once and in canonical order;
- speaker and overlap boundaries remain chronological.

## 3. Broader text scan

Scan the complete SRT as text for new systematic issues. Do not spend time measuring
player synchronization in this pass. Report PASS/FAIL for micro-cues, nonfinal one-line
cues, orphaned final words, ordering, duplication, and speaker transitions.

Send the three hashes, all three printed excerpts, the broader scan result, and
`git status --short`. Generated exports remain outside Git; do not copy or commit
`LICENSE_SKETCH.TXT`.
