# Retest long-form subtitle fragmentation and timing

This retest regenerates subtitles from the retained P9-02 canonical result after the
micro-cue boundary fix. It does not load models or rerun transcription.

## 0. Synchronize and restore the review paths

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check

export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_LONG_SUB_AUDIO="$EWP_TESTDATA/audio/p9-02-long-two-speakers-polish.mp3"
export EWP_LONG_SUB_RESULT="$EWP_TESTDATA/phase9-long-gGsPOpsQ/output/P9-02/p9-02-long-two-speakers-polish_results.json"
export EWP_LONG_SUB_ROOT="$EWP_TESTDATA/release-long-subtitles-wCI5Br3A"
export EWP_LONG_SUB_OUTPUT="$EWP_LONG_SUB_ROOT/output"

test -s "$EWP_LONG_SUB_AUDIO" && echo "P9-02 audio: present"
test -s "$EWP_LONG_SUB_RESULT" && echo "P9-02 canonical result: present"
test -d "$EWP_LONG_SUB_OUTPUT" && echo "review output: present"
```

Expected commit: `72b43a3` or later and 271 passing tests.

## 1. Regenerate derived subtitles

```bash
CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber export "$EWP_LONG_SUB_RESULT" \
    --output-dir "$EWP_LONG_SUB_OUTPUT" \
    --format srt --format vtt --force

export EWP_LONG_SUB_SRT_V2="$EWP_LONG_SUB_OUTPUT/p9-02-long-two-speakers-polish_subtitles_v002.srt"
export EWP_LONG_SUB_VTT_V2="$EWP_LONG_SUB_OUTPUT/p9-02-long-two-speakers-polish_subtitles_v002.vtt"
test -s "$EWP_LONG_SUB_SRT_V2" && echo "repaired long SRT: present"
test -s "$EWP_LONG_SUB_VTT_V2" && echo "repaired long VTT: present"
sha256sum "$EWP_LONG_SUB_RESULT" "$EWP_LONG_SUB_SRT_V2" "$EWP_LONG_SUB_VTT_V2"
```

## 2. Recheck the reported fragmentation window

```bash
awk '
    /00:08:00/ {show=1}
    show {print}
    /00:08:18/ {exit}
' "$EWP_LONG_SUB_SRT_V2"
```

Confirm that `bo`, `nawet`, and `błędu.` are no longer independent micro-cues and that
the passage reads naturally. Report the displayed excerpt if it still fragments.

## 3. Check timing independently of layout

Play the revised SRT against the original P9-02 audio. Check at least these regions:

- the first two minutes;
- around `00:08:00`;
- around `00:24:00`;
- the final two minutes.

At each checkpoint record one of `on time`, `early`, or `late`. For every early or late
checkpoint, record:

```text
subtitle cue start shown in SRT:
audible start of the cue's first word (player position):
approximate difference in seconds:
cue text:
```

Judge timing from the first word of the cue, not from when later words in the two-line cue
are spoken: showing the complete cue while it is being spoken is normal. If the difference
changes across the episode, retain all measured checkpoints; do not apply a global offset.

## 4. Finish the representativeness review

If timing is acceptable, complete the full SRT playback and text scan from the original
long-review runbook. WebVTT needs only beginning/middle/end and speaker-transition spot
checks because it uses the same cues.

Send:

- the three hashes;
- the `00:08` excerpt;
- the four timing checkpoint observations and measured differences;
- final SRT and WebVTT PASS/FAIL;
- `git status --short` output.

Generated evidence remains outside Git. Do not copy or commit `LICENSE_SKETCH.TXT`.
