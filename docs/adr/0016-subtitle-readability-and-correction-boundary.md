# ADR-0016: Subtitle readability and correction boundary

- Status: proposed
- Date: 2026-08-05

## Decision

Subtitle generation may merge adjacent non-overlapping fragments from the same speaker
across a configurable short pause when the combined cue still meets duration,
reading-speed, and line limits. The default maximum merge gap is 1200 ms. This operation
changes only derived cues; it does not change canonical words or timestamps.

The immutable canonical result remains the source for all exports. TXT, SRT, and WebVTT
will not be maintained as independent correction documents. A later versioned correction
layer will map editorial changes to canonical timed words and regenerate every export
together.

## Evidence and reason

Commit `47b25af` or later passed 257 automated tests before the first external-player
review. The Ubuntu 24.04 WSL2 RTX 3090 workstation ran
[`RUN_RELEASE_PRIVATE_YOUTUBE_SUBTITLES.md`](../../WSL%20config/RUN_RELEASE_PRIVATE_YOUTUBE_SUBTITLES.md)
against P2-03. Both SRT and WebVTT uploaded to YouTube successfully and rendered Polish
characters correctly. The reviewed artifacts were:

```text
11c72f004050e424ccaf575a3fb596d829c1b70435b911772c21ab445b67763a  p2-03-private-review.mp4
3da1957eb55756ab72639d3c3199f02fbbd8839d815e6329458e33dff20865c7  p2-03-mixed-stereo_subtitles.srt
c9db83c148ef389d92f1b19e8b2401981c1a9b483d2fb0aa9761f2c3f05330a5  p2-03-mixed-stereo_subtitles.vtt
```

The readability gate failed for both formats. Short fragments such as `a co`, `Może i`,
and isolated words around emphatic pauses disappeared too quickly or were detached from
the rest of their sentence. YouTube also displayed an informational warning that some
WebVTT formatting might be lost; text and Polish characters were unaffected.

Commit `11bd748` activates constrained same-speaker cue merging, raises the default
merge gap from 300 to 1200 ms, documents platform format roles and the correction
boundary, and passes 258 automated tests. External-player re-review remains required
before this ADR becomes accepted.

## Consequences

- short rhetorical pauses can remain inside a readable subtitle cue;
- different speakers and explicit overlap are never merged by this rule;
- maximum duration, line, and reading-speed limits remain authoritative;
- existing canonical JSON can be re-exported without source audio, GPU, or ASR;
- SRT is the conservative platform interchange, WebVTT is the browser-native caption
  track, and custom synchronized web transcripts should use timed JSON plus accessible
  HTML;
- editorial import, sentence correction, speaker colors, and cross-platform publishing
  presets remain Version 2 work.
