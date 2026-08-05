# Validate long-form subtitle timing in YouTube Studio

This final supplementary check validates the accepted P9-02 SRT timeline in the same
platform used for the MVP compatibility gate. Text splitting is already accepted.

## 0. Synchronize and locate retained evidence

```bash
cd ~/transkrypcje/ewp-transcripts
git pull --ff-only
git log -1 --oneline
uv sync --locked
make check

export EWP_TESTDATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export EWP_LONG_SUB_AUDIO="$EWP_TESTDATA/audio/p9-02-long-two-speakers-polish.mp3"
export EWP_LONG_SUB_OUTPUT="$EWP_TESTDATA/release-long-subtitles-wCI5Br3A/output"
export EWP_LONG_SUB_SRT_V4="$EWP_LONG_SUB_OUTPUT/p9-02-long-two-speakers-polish_subtitles_v004.srt"
export EWP_LONG_SUB_TIMING_VIDEO="$EWP_TESTDATA/release-long-subtitles-wCI5Br3A/p9-02-youtube-timing.mp4"

test -s "$EWP_LONG_SUB_AUDIO" && echo "P9-02 audio: present"
test -s "$EWP_LONG_SUB_SRT_V4" && echo "accepted long SRT: present"
```

Expected commit: `078df8c` or later and 273 passing tests.

## 1. Create a low-bitrate blank review video

```bash
ffmpeg -hide_banner -y \
    -f lavfi -i 'color=c=black:s=1280x720:r=1' \
    -i "$EWP_LONG_SUB_AUDIO" \
    -map 0:v:0 -map 1:a:0 \
    -c:v libx264 -preset veryfast -crf 35 -pix_fmt yuv420p \
    -c:a aac -b:a 128k \
    -metadata:s:a:0 language=pol \
    -shortest -movflags +faststart \
    "$EWP_LONG_SUB_TIMING_VIDEO"

ffprobe -v error \
    -show_entries stream=codec_name,codec_type:format=duration \
    -of default=noprint_wrappers=1 "$EWP_LONG_SUB_TIMING_VIDEO"
sha256sum "$EWP_LONG_SUB_TIMING_VIDEO" "$EWP_LONG_SUB_SRT_V4"
```

The black frame minimizes video size. AAC conversion is expected because MP3 audio is not
the conservative MP4 delivery choice.

## 2. Upload privately and set language

Upload the MP4 to YouTube Studio as **Private**. Before adding captions, explicitly set
the video language to **Polish** in video details; do not rely on container metadata or
automatic language detection. Upload the accepted v4 SRT as Polish captions without
automatic timing.

Wait until YouTube finishes processing the resolution used for review.

## 3. Timing checkpoints

Review the first two minutes, around `00:08:00`, around `00:16:00`, around `00:24:00`,
and the final two minutes. Also inspect at least five speaker transitions distributed
throughout the episode.

At each checkpoint report:

```text
checkpoint:
timing: on time / early / late
estimated offset if not on time:
cue text or number:
```

At `00:08:14–00:08:18`, determine whether the visible gap corresponds to actual silence.
Do not count seeing the full two-line cue while its later words are still being spoken as
an early subtitle; judge from the cue's first displayed word.

## 4. Result

Report overall timing PASS/FAIL, checkpoint observations, player/browser, the two hashes,
and `git status --short`. If timing fails, provide at least three measured offsets. Do not
apply a global offset when the differences are not constant. The generated MP4 and
captions remain outside Git; do not commit `LICENSE_SKETCH.TXT`.
