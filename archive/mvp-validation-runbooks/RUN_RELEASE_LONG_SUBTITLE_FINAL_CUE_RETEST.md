# Retest final-cue balancing on the long subtitle sample

This export-only retest checks the last known text-layout defect. Do not evaluate player
pacing yet.

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check

export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_LONG_SUB_RESULT="$EWP_TESTDATA/phase9-long-gGsPOpsQ/output/P9-02/p9-02-long-two-speakers-polish_results.json"
export EWP_LONG_SUB_OUTPUT="$EWP_TESTDATA/release-long-subtitles-wCI5Br3A/output"

CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber export "$EWP_LONG_SUB_RESULT" \
    --output-dir "$EWP_LONG_SUB_OUTPUT" \
    --format srt --format vtt --force

export EWP_LONG_SUB_SRT_V4="$EWP_LONG_SUB_OUTPUT/p9-02-long-two-speakers-polish_subtitles_v004.srt"
export EWP_LONG_SUB_VTT_V4="$EWP_LONG_SUB_OUTPUT/p9-02-long-two-speakers-polish_subtitles_v004.vtt"
test -s "$EWP_LONG_SUB_SRT_V4" && echo "final-balanced SRT: present"
test -s "$EWP_LONG_SUB_VTT_V4" && echo "final-balanced VTT: present"
sha256sum "$EWP_LONG_SUB_RESULT" "$EWP_LONG_SUB_SRT_V4" "$EWP_LONG_SUB_VTT_V4"

awk '
    /00:08:00/ {show=1}
    show {print}
    show && /00:08:18/ {exit}
' "$EWP_LONG_SUB_SRT_V4"

git status --short
```

Expected commit: `f095ef3` or later and 273 passing tests. Confirm that the final fragment
around `za mały margines błędu` is balanced into two lines or redistributed into adjacent
cues without duplication, omission, micro-cues, or timestamp overlap. If it passes, scan
the full SRT text once more for avoidable one-line cues inside multi-cue turns. Send the
three hashes, excerpt, scan result, and Git status. Generated files remain outside Git.
