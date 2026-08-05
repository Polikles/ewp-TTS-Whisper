# Extract canonical windows for long subtitle failures

Run this model-free diagnostic after synchronizing commit `8382488` or later. It prints
only the three reported P9-02 regions needed to build turn-level partitioning regressions.

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only

export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_LONG_SUB_RESULT="$EWP_TESTDATA/phase9-long-gGsPOpsQ/output/P9-02/p9-02-long-two-speakers-polish_results.json"
export EWP_LONG_SUB_WINDOWS="$EWP_TESTDATA/release-long-subtitles-wCI5Br3A/canonical-failure-windows.json"

uv run --locked python tools/extract_canonical_windows.py \
    "$EWP_LONG_SUB_RESULT" \
    --window 475000:496000 \
    --window 1525000:1570000 \
    --window 2058000:2075000 \
    > "$EWP_LONG_SUB_WINDOWS"

test -s "$EWP_LONG_SUB_WINDOWS" && echo "canonical failure windows: present"
sha256sum "$EWP_LONG_SUB_RESULT" "$EWP_LONG_SUB_WINDOWS"
cat "$EWP_LONG_SUB_WINDOWS"
git status --short
```

Send the two hashes and complete JSON output. The output intentionally contains the
transcript text in these narrow windows. It remains outside Git.
