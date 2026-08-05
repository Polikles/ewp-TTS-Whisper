# Review SRT and VTT in a private YouTube upload

This manual release gate validates subtitle readability in the target web player. It uses
the short, clean, two-speaker P2-03 fixture so speaker changes and timing are visible
without uploading a full episode.

This is an explicit external disclosure performed by the operator, not an application
feature. The transcription pipeline itself remains local-only. Use only audio you are
authorized to upload, select **Private** visibility, do not expose links, and delete the
video after recording the review result if continued hosting is unnecessary.

## 0. Synchronize and create local review material

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check

export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_SUB_REVIEW_INPUT="$EWP_TESTDATA/audio/p2-03-mixed-stereo.wav"
export EWP_SUB_REVIEW_ROOT="$(mktemp -d "$EWP_TESTDATA/release-subtitles-XXXXXXXX")"
export EWP_SUB_REVIEW_OUTPUT="$EWP_SUB_REVIEW_ROOT/output"
export EWP_SUB_REVIEW_WORK="$EWP_SUB_REVIEW_ROOT/work"
mkdir -p "$EWP_SUB_REVIEW_OUTPUT" "$EWP_SUB_REVIEW_WORK"

test -s "$EWP_SUB_REVIEW_INPUT" && echo "P2-03 source: present"
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
printf 'sandbox=%s\n' "$EWP_SUB_REVIEW_ROOT"
```

Expected commit: `11bd748` or later and 258 passing tests.

## 1. Generate the two-speaker result and subtitles offline

```bash
cat > "$EWP_SUB_REVIEW_ROOT/transcriber.toml" <<EOF
[general]
language = "pl"
offline = true
interactive = false
[runtime]
work_root = "$EWP_SUB_REVIEW_WORK"
EOF

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber transcribe "$EWP_SUB_REVIEW_INPUT" \
    --config "$EWP_SUB_REVIEW_ROOT/transcriber.toml" \
    --speaker-count 2 --output-dir "$EWP_SUB_REVIEW_OUTPUT" --non-interactive

export EWP_SUB_REVIEW_SRT="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_subtitles.srt"
export EWP_SUB_REVIEW_VTT="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_subtitles.vtt"
test -s "$EWP_SUB_REVIEW_SRT" && echo "SRT: present"
test -s "$EWP_SUB_REVIEW_VTT" && echo "VTT: present"
```

## 2. Create a temporary uploadable video

YouTube does not accept an audio-only upload. Create a local black-background MP4 without
embedding transcript text:

```bash
export EWP_SUB_REVIEW_VIDEO="$EWP_SUB_REVIEW_ROOT/p2-03-private-review.mp4"
ffmpeg -v error -y \
    -f lavfi -i 'color=c=black:s=1280x720:r=25' \
    -i "$EWP_SUB_REVIEW_INPUT" \
    -map 0:v:0 -map 1:a:0 \
    -c:v libx264 -preset veryfast -tune stillimage -pix_fmt yuv420p \
    -c:a aac -b:a 192k -metadata:s:a:0 language=pol \
    -shortest "$EWP_SUB_REVIEW_VIDEO"

ffprobe -v error -show_entries format=duration \
    -show_entries stream=codec_name,codec_type \
    -of default=noprint_wrappers=1 "$EWP_SUB_REVIEW_VIDEO"
sha256sum "$EWP_SUB_REVIEW_VIDEO" "$EWP_SUB_REVIEW_SRT" "$EWP_SUB_REVIEW_VTT"
```

## 3. Review SRT in YouTube

1. Upload `p2-03-private-review.mp4` through YouTube Studio.
2. Set visibility to **Private** before completing the upload.
3. In **Details → Show more → Language and captions certification**, set the original
   video language to **Polish**. YouTube may otherwise infer or apply a channel-default
   language even when the MP4 audio stream is tagged `pol`.
4. Disable automatic publication and do not share the private invitation.
5. In **Subtitles**, select Polish and upload `p2-03-mixed-stereo_subtitles.srt` with
   timing.
6. Watch the complete 105-second video with subtitles enabled at normal speed.
7. Record PASS/FAIL for every criterion below.

## 4. Review VTT separately

Delete or replace the Polish subtitle track, then upload
`p2-03-mixed-stereo_subtitles.vtt` with timing. Watch the complete video again. If the UI
does not allow replacing the track unambiguously, create a second Private upload of the
same MP4 and use only the VTT track there.

## 5. Acceptance checklist

Record separate SRT and VTT outcomes:

```text
SRT
[ ] upload accepted without parser/timestamp errors
[ ] Polish characters render correctly
[ ] no cue exceeds two visible lines
[ ] cues do not overlap accidentally
[ ] cues appear and disappear at intelligible speech boundaries
[ ] speaker labels change correctly and are not repeated unnecessarily
[ ] reading speed is comfortable at normal playback speed
[ ] no subtitle remains visible through an unrelated silence or speaker turn

VTT
[ ] upload accepted without parser/timestamp errors
[ ] Polish characters render correctly
[ ] no cue exceeds two visible lines
[ ] cues do not overlap accidentally
[ ] cues appear and disappear at intelligible speech boundaries
[ ] speaker labels change correctly and are not repeated unnecessarily
[ ] reading speed is comfortable at normal playback speed
[ ] no subtitle remains visible through an unrelated silence or speaker turn
```

The gate passes only if every item passes for both formats. Report any failing timestamp
and the visible failure; do not include private transcript text unless needed to diagnose
the issue.

## 6. Cleanup and evidence

After the review, keep or delete the Private upload according to your privacy preference.
Local generated files are outside Git and may be removed with the entire sandbox after
recording:

```bash
test -z "$(find "$EWP_SUB_REVIEW_WORK" -mindepth 2 -maxdepth 2 -type d -print)" \
    && echo "subtitle review workdir cleanup: PASS"
git status --short
```

Send the two completed checklists, the three hashes from section 2, and whether the
Private video was retained or deleted. Do not copy or commit `LICENSE_SKETCH.TXT`.

## 7. Re-review after cue-readability tuning

The first review on 2026-08-05 found isolated one- or two-word cues around rhetorical
pauses. Commit `11bd748` makes the configured `max_merge_gap_ms` effective and changes
its default to 1200 ms. If the canonical result and review MP4 from the first attempt
still exist, do not rerun ASR or rebuild the video. Regenerate only the derived captions:

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check

export EWP_SUB_REVIEW_ROOT="$HOME/transkrypcje/ewp-transcripts-testdata/phase0/release-subtitles-rG9E4ZHD"
export EWP_SUB_REVIEW_OUTPUT="$EWP_SUB_REVIEW_ROOT/output"
export EWP_SUB_REVIEW_RESULT="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_results.json"
export EWP_SUB_REVIEW_CONFIG="$EWP_SUB_REVIEW_ROOT/transcriber.toml"
export EWP_SUB_REVIEW_SRT_V2="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_subtitles_v002.srt"
export EWP_SUB_REVIEW_VTT_V2="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_subtitles_v002.vtt"

test -s "$EWP_SUB_REVIEW_RESULT" && echo "canonical result: present"
test -s "$EWP_SUB_REVIEW_ROOT/p2-03-private-review.mp4" && echo "review video: present"

CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber export "$EWP_SUB_REVIEW_RESULT" \
    --config "$EWP_SUB_REVIEW_CONFIG" \
    --format srt --format vtt --force

test -s "$EWP_SUB_REVIEW_SRT_V2" && echo "revised SRT: present"
test -s "$EWP_SUB_REVIEW_VTT_V2" && echo "revised VTT: present"
sha256sum "$EWP_SUB_REVIEW_RESULT" "$EWP_SUB_REVIEW_SRT_V2" "$EWP_SUB_REVIEW_VTT_V2"
git status --short
```

Upload the `_v002` files using sections 3–5. Pay particular attention to the previously
failing fragments `a co`, `Może i … nikt nie zauważy`, and speech separated by an
approximately one-second emphatic pause. The test passes only when the complete SRT and
VTT checklists pass; a YouTube notice about unsupported extra VTT formatting is
informational if the text, timing, and Polish characters remain correct.

## 8. Re-review after orphan-fragment balancing

The `_v002` review improved pacing but still found one-to-three-word pieces stranded at
capacity-based sentence splits. Commit `479004a` adds a soft four-word balancing target
using canonical word timestamps. It does not combine a punctuated short sentence across
silence, another speaker, or overlap. Reuse the same canonical result and MP4 again:

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check

export EWP_SUB_REVIEW_ROOT="$HOME/transkrypcje/ewp-transcripts-testdata/phase0/release-subtitles-rG9E4ZHD"
export EWP_SUB_REVIEW_OUTPUT="$EWP_SUB_REVIEW_ROOT/output"
export EWP_SUB_REVIEW_RESULT="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_results.json"
export EWP_SUB_REVIEW_CONFIG="$EWP_SUB_REVIEW_ROOT/transcriber.toml"
export EWP_SUB_REVIEW_SRT_V3="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_subtitles_v003.srt"
export EWP_SUB_REVIEW_VTT_V3="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_subtitles_v003.vtt"

CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber export "$EWP_SUB_REVIEW_RESULT" \
    --config "$EWP_SUB_REVIEW_CONFIG" \
    --format srt --format vtt --force

test -s "$EWP_SUB_REVIEW_SRT_V3" && echo "balanced SRT: present"
test -s "$EWP_SUB_REVIEW_VTT_V3" && echo "balanced VTT: present"
sha256sum "$EWP_SUB_REVIEW_RESULT" "$EWP_SUB_REVIEW_SRT_V3" "$EWP_SUB_REVIEW_VTT_V3"
git status --short
```

Repeat sections 3–5 with `_v003`. Confirm specifically that sentence fragments are no
longer stranded, while genuinely short statements surrounded by silence still appear as
independent cues.

## 9. Re-review linguistic cue and line boundaries

The `_v003` review found one labelled speaker-change fragment and Polish connective
words stranded at cue or line endings. Commit `fc0ac29` corrects label-capacity accounting
and adds linguistic boundary preferences. Generate version 4 from the same result:

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check

export EWP_SUB_REVIEW_ROOT="$HOME/transkrypcje/ewp-transcripts-testdata/phase0/release-subtitles-rG9E4ZHD"
export EWP_SUB_REVIEW_OUTPUT="$EWP_SUB_REVIEW_ROOT/output"
export EWP_SUB_REVIEW_RESULT="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_results.json"
export EWP_SUB_REVIEW_CONFIG="$EWP_SUB_REVIEW_ROOT/transcriber.toml"
export EWP_SUB_REVIEW_SRT_V4="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_subtitles_v004.srt"
export EWP_SUB_REVIEW_VTT_V4="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_subtitles_v004.vtt"

CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber export "$EWP_SUB_REVIEW_RESULT" \
    --config "$EWP_SUB_REVIEW_CONFIG" \
    --format srt --format vtt --force

test -s "$EWP_SUB_REVIEW_SRT_V4" && echo "linguistic SRT: present"
test -s "$EWP_SUB_REVIEW_VTT_V4" && echo "linguistic VTT: present"
sha256sum "$EWP_SUB_REVIEW_RESULT" "$EWP_SUB_REVIEW_SRT_V4" "$EWP_SUB_REVIEW_VTT_V4"
git status --short
```

Repeat sections 3–5 with `_v004`. Verify the complete files and specifically confirm
that `Speaker2: Może i` is no longer detached and that connective words are not stranded
at line or cue endings when a readable alternative exists.

## 10. Re-review stabilized multi-cue chains

The `_v004` review supplied a three-cue chain that a single balancing pass could not
fully repair. Commit `6545355` repeats merge and balance passes until stable and adds the
reported timing pattern as a regression test. Generate version 5 without ASR:

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check

export EWP_SUB_REVIEW_ROOT="$HOME/transkrypcje/ewp-transcripts-testdata/phase0/release-subtitles-rG9E4ZHD"
export EWP_SUB_REVIEW_OUTPUT="$EWP_SUB_REVIEW_ROOT/output"
export EWP_SUB_REVIEW_RESULT="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_results.json"
export EWP_SUB_REVIEW_CONFIG="$EWP_SUB_REVIEW_ROOT/transcriber.toml"
export EWP_SUB_REVIEW_SRT_V5="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_subtitles_v005.srt"
export EWP_SUB_REVIEW_VTT_V5="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_subtitles_v005.vtt"

CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber export "$EWP_SUB_REVIEW_RESULT" \
    --config "$EWP_SUB_REVIEW_CONFIG" \
    --format srt --format vtt --force

test -s "$EWP_SUB_REVIEW_SRT_V5" && echo "stabilized SRT: present"
test -s "$EWP_SUB_REVIEW_VTT_V5" && echo "stabilized VTT: present"
sha256sum "$EWP_SUB_REVIEW_RESULT" "$EWP_SUB_REVIEW_SRT_V5" "$EWP_SUB_REVIEW_VTT_V5"
git status --short
```

Repeat sections 3–5 with `_v005`. Recheck the complete file, the supplied 15–22 second
Speaker2 transition, the `Tak się` / `dzieje` chain near 36 seconds, and all remaining
single-word cues. Report any remaining connective ending with its complete two-line cue
so hard-capacity constraints can be distinguished from a selectable bad boundary.

## 11. Re-review canonical word-boundary search

The `_v005` review and canonical JSON diagnostic demonstrated that valid repairs can
require moving several words at once; a one-word greedy transfer may pass through an
invalid intermediate state. Commit `c23dd71` searches all valid neighboring word splits
and includes the exact reported timings as regressions. Generate version 6:

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check

export EWP_SUB_REVIEW_ROOT="$HOME/transkrypcje/ewp-transcripts-testdata/phase0/release-subtitles-rG9E4ZHD"
export EWP_SUB_REVIEW_OUTPUT="$EWP_SUB_REVIEW_ROOT/output"
export EWP_SUB_REVIEW_RESULT="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_results.json"
export EWP_SUB_REVIEW_CONFIG="$EWP_SUB_REVIEW_ROOT/transcriber.toml"
export EWP_SUB_REVIEW_SRT_V6="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_subtitles_v006.srt"
export EWP_SUB_REVIEW_VTT_V6="$EWP_SUB_REVIEW_OUTPUT/p2-03-mixed-stereo_subtitles_v006.vtt"

CUDA_VISIBLE_DEVICES="" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --locked transcriber export "$EWP_SUB_REVIEW_RESULT" \
    --config "$EWP_SUB_REVIEW_CONFIG" \
    --format srt --format vtt --force

test -s "$EWP_SUB_REVIEW_SRT_V6" && echo "searched SRT: present"
test -s "$EWP_SUB_REVIEW_VTT_V6" && echo "searched VTT: present"
sha256sum "$EWP_SUB_REVIEW_RESULT" "$EWP_SUB_REVIEW_SRT_V6" "$EWP_SUB_REVIEW_VTT_V6"
git status --short
```

Repeat sections 3–5 with `_v006`. Recheck the complete file and the exact previously
failing ranges at 15–22, 35–39, and 96–105 seconds. The gate passes only if there are no
avoidable micro-cues or protected Polish words stranded at visible line endings.
