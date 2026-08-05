# ADR-0016: Subtitle readability and correction boundary

- Status: accepted
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

The second review regenerated exports from the unchanged canonical result:

```text
2086aa699bc489c02718077f8ebc72aa61087ac1598cb3d626defee38074962a  p2-03-mixed-stereo_results.json
93d132e785b87a1b6cbe2dd5299bd68ba7347ab58225b7ef14b8019674e65545  p2-03-mixed-stereo_subtitles_v002.srt
0c514003a913386ea978d70cc0b1ea7a84febcc86a4e9a77e4675d2aa9a0e31a  p2-03-mixed-stereo_subtitles_v002.vtt
```

Pacing improved, but the gate still failed: capacity-based cue splitting left some
one-to-three-word beginnings or endings of longer sentences isolated. These differ from
legitimate short utterances surrounded by silence, which must remain independent. The
next implementation therefore treats a minimum word count as a soft balancing target
inside a continuous canonical segment while preserving punctuation boundaries, silence,
speaker changes, and every hard subtitle constraint.

The `_v003` review confirmed another material improvement, and SRT and WebVTT behaved
functionally the same in YouTube. One speaker-change cue still stranded the label and two
opening words (`Speaker2: Może i`) from the continuation. Some line and cue boundaries
also ended with Polish connectives such as `i`, `że`, `z`, `bo`, or `w`. The cause was
twofold: capacity was conservatively reserved for a label on continuation chunks even in
`on-change` mode, and wrapping optimized only maximum length rather than linguistic
boundaries.

Commit `fc0ac29` reserves label capacity only where a label is rendered, balances the
labelled first cue against its unlabeled continuation, moves connective words to the
following timed cue when hard constraints permit, and selects balanced line breaks that
avoid nonfinal connectives. It passes 264 automated tests. A final external-player review
is still required before this ADR becomes accepted.

The `_v004` review confirmed that conjunction handling worked well and that subtitles
were much better overall. It still exposed two single-word micro-cues, again detached
the opening `Speaker2: Może i`, and found `to` and `na` at two line endings. The accepted
v4 evidence is:

```text
2086aa699bc489c02718077f8ebc72aa61087ac1598cb3d626defee38074962a  p2-03-mixed-stereo_results.json
1af2655f3f7cf278fdf94beaa60ec86b94e7c50d1f63e11b17d63b56a64e23e4  p2-03-mixed-stereo_subtitles_v004.srt
144ec38e729cfcabe6bd829a4cb424379a0fd9fce6c4d81a81c9ef42a5ae83ac  p2-03-mixed-stereo_subtitles_v004.vtt
```

The supplied excerpt showed a three-cue dependency: a two-word labelled opening, a
one-word middle cue, and a long continuation. A single left-to-right balancing pass could
repair the middle cue but did not revisit the opening afterward. Commit `6545355` repeats
merge and balance passes until the chain stabilizes, protects `to` in addition to the
existing Polish boundary list, and tests the reported timing pattern directly. It passes
267 automated tests. External-player review remains pending.

The `_v005` output remained unchanged at the reported locations. Its evidence is:

```text
2086aa699bc489c02718077f8ebc72aa61087ac1598cb3d626defee38074962a  p2-03-mixed-stereo_results.json
3ab34169aad4aee4fd6ddd1640aa1817b61877668d494e6ca99e7f85245fb31a  p2-03-mixed-stereo_subtitles_v005.srt
c82b52084efdb533c832bca9cd8ece374da684a20ba43b6d2e03d4d96b49c50c  p2-03-mixed-stereo_subtitles_v005.vtt
```

Inspection of the canonical words showed why. The sequence was one 20-word canonical
segment, not three source segments. Moving only `nie` into the `nikt` cue temporarily
exceeded the 20 CPS limit, but moving several timed words produced a valid cue. The
greedy balancer stopped on that first invalid intermediate state. The remaining `na`
was inside a two-line cue; removing it required moving `przedsiębiorstwo` across the next
cue boundary so both cues could rewrap validly.

Commit `c23dd71` searches all valid word boundaries across neighboring fragments and
ranks them by protected-word placement, orphan avoidance, boundary movement, and balance.
Regression tests use the operator-provided canonical text and exact timings for both
failures. The implementation passes 268 automated tests. External-player acceptance is
still pending.

The `_v006` review passed the previously failing micro-cue and protected-word cases and
was judged much better overall. SRT and WebVTT remained functionally equivalent. One
continuous sentence still produced a single-line cue between otherwise two-line cues:

```text
danych przez przedsiębiorstwo, to faktycznie
```

Together with its continuation, the text is exactly 100 characters and can wrap cleanly
as 50 and 49 characters. The v6 evidence is:

```text
2086aa699bc489c02718077f8ebc72aa61087ac1598cb3d626defee38074962a  p2-03-mixed-stereo_results.json
d0ff4847d88135ad5e19fc8390dbdb58a608701d159f76139fa9ff3eec62f787  p2-03-mixed-stereo_subtitles_v006.srt
ec7ec0ed88605bbdbdf03fb18b22683df7f5826e65c3cc78c3f3318e9597cf6d  p2-03-mixed-stereo_subtitles_v006.vtt
```

Commit `b0f7374` retains 42 characters as the preferred target but raises the hard line
ceiling from 46 to 50. This is an application preset choice, not a container or YouTube
requirement. The exact reported continuation now forms one balanced two-line cue, and
all 269 automated tests pass. External-player acceptance remains pending.

The `_v007` review confirmed the flexible ceiling but clarified the remaining aesthetic
rule: in a continuous multi-cue speaker turn, a one-line cue is acceptable only at the
end. A turn consisting of one short cue is also valid. Several nonfinal one-line cues
remained, including the labelled Speaker2 opening and short complete sentences within
Speaker1's longer turn. The v7 evidence is:

```text
2086aa699bc489c02718077f8ebc72aa61087ac1598cb3d626defee38074962a  p2-03-mixed-stereo_results.json
94f89fd6d45fd0ece2818eaa7e5986757ebedf2ae44df5537c0f29ab4652dcda  p2-03-mixed-stereo_subtitles_v007.srt
adfab9d254c9ae4aae71a558b41aa0641eb3c381113de2f55f9cba6260e761d7  p2-03-mixed-stereo_subtitles_v007.vtt
```

Commit `17f5d86` adds a turn-level line-count penalty to neighboring boundary search and
allows a sentence boundary to move when the same speaker continues without material
silence. It preserves one-line final turns and silence-separated short statements. The
implementation passes 270 automated tests. External-player acceptance remains pending.

The `_v008` SRT and WebVTT exports passed the complete manual review and were judged very
good. The operator confirmed the turn-level one-line rule and all previous readability
defects were resolved. Accepted evidence:

```text
2086aa699bc489c02718077f8ebc72aa61087ac1598cb3d626defee38074962a  p2-03-mixed-stereo_results.json
b1fb69469a2aae399e221d202c642f44886f7e69f455fa101e3960ea737b89f9  p2-03-mixed-stereo_subtitles_v008.srt
0bc9b1d5ad30c7b61c42edadf086e28971a3bb6b058972579b849f1fca63e6f4  p2-03-mixed-stereo_subtitles_v008.vtt
```

This accepts the MVP subtitle algorithm and YouTube compatibility gate on the 105-second
two-speaker P2-03 fixture. Because the fixture is short, a separate long-form local-player
review remains useful as additional representativeness evidence, not as a condition for
this decision.

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
