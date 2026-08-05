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
[`RUN_RELEASE_PRIVATE_YOUTUBE_SUBTITLES.md`](../../archive/mvp-validation-runbooks/RUN_RELEASE_PRIVATE_YOUTUBE_SUBTITLES.md)
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

The first supplementary long-form review used the existing 34.7-minute P9-02 canonical
result. It found a new fragmentation case around `00:08:13`: rapid aligned words were
exported as several 40–441 ms cues (`bo`, `nawet`, `110% ma za mały margines`, and
`błędu.`). It also reported inconsistent apparent lead relative to the audio: accurate at
the beginning, roughly two cues ahead around minute 24, and still two or three words
ahead near the end. The SRT and WebVTT evidence hashes were:

```text
41c4fa5e7368a3ae94b60e8a0071c9e575033a4db54682311cde734136f1e751  p9-02-long-two-speakers-polish_results.json
44b340a8f123f2daa11cdf23affd8654f1ac600dc41cd15a3fc7000fe862b499  p9-02-long-two-speakers-polish_subtitles.srt
b22d2d5d39ab0e53d156a27117bde4f57f650ed14f74c135a934935e6fab0d56  p9-02-long-two-speakers-polish_subtitles.vtt
```

Commit `72b43a3` fixes the fragmentation bug. The neighboring-boundary search had allowed
an invalid original split to remain its best candidate, so valid redistributions could
lose to a cue that violated the intended pacing constraints. A regression based on the
reported passage now rejects those micro-cues. The timing observation remains separate:
the retest must establish whether the lead persists after fragmentation is removed and,
if so, compare canonical word time with the audible time before any timing correction is
designed.

The `_v002` long-form retest proved that commit `72b43a3` did not repair the real P9-02
chain. The same micro-cues remained, along with nonfinal one-line cues, an orphaned final
word (`metody.`), and an overlapping split (`Nie` followed by `zapomnijcie`) near the end.
This disproves pairwise boundary repair as a sufficient general solution. The next design
must partition complete continuous same-speaker word chains while respecting canonical
segment, overlap, timing, and speaker boundaries. Exact canonical windows are required as
regression fixtures before that change.

The apparent timing concern is deferred until text partitioning is stable. VLC produced
inconsistent pacing, while Subtitle Edit 5.1 was materially better. Final pacing will be
checked with a blank video in YouTube Studio rather than inferred from VLC playback.

Canonical-window evidence hash
`eeb7d4ad8fba567d2f186d5c4e7c075145b27354f46e7d90ca64eeb108100a77`
confirmed the structural causes. The rapid fragment is one 25-word ordinary segment;
`metody.` is inside one 19-word overlap-marked segment; and `Nie zapomnijcie…` is one
six-word overlap-marked segment whose first word spans only 100 ms. Commit `c15ccaa`
therefore replaces preservation of greedy splits with bounded dynamic programming over
complete continuous word chains. Speaker changes, overlap-status changes, missing word
timings, negative gaps, and pauses above 1.2 seconds remain hard boundaries. Line count,
line length, and maximum cue duration remain hard constraints. Minimum word count,
minimum readable duration, nonfinal two-line layout, connective placement, sentence
boundaries, cue count, and line utilization form the ordered optimization criteria.

Some rapid aligned speech has no exact word-boundary partition below 20 characters per
second. In that case coherence wins over creating unreadable micro-cues, and derived cue
display duration is extended toward the configured readability rate where the following
timeline permits. Canonical word timestamps remain unchanged.

The P9-02 `_v003` retest was almost perfect and eliminated the reported micro-cues,
overlap split, and orphan words. Evidence hashes were:

```text
41c4fa5e7368a3ae94b60e8a0071c9e575033a4db54682311cde734136f1e751  p9-02-long-two-speakers-polish_results.json
613348a73cbc246151c078027f65008754a229c618f7beacf90f7d033955ea05  p9-02-long-two-speakers-polish_subtitles_v003.srt
2826d08d5a80ce5e6f442a2d9bf02451303efe4dfc093c24b322e231544fa0a3  p9-02-long-two-speakers-polish_subtitles_v003.vtt
```

One avoidable final one-line cue remained inside a multi-cue continuous chain (`za mały
margines błędu.`). Commit `f8aad6a` makes this a soft penalty for both nonfinal and final
cues whenever the chain contains multiple cues. A truly short chain consisting of one
cue remains valid. The silence or alignment gap from roughly `00:08:14.8` to `00:08:18.6`
is not closed by moving canonical words; timing validation remains deferred to YouTube
Studio after text layout passes.

The P9-02 `_v004` retest passed the long-form text-layout gate. The previously short final
fragment is contained within two lines, no avoidable one-line cues remain, and the only
one-line cues are legitimate silence-separated utterances. Accepted long-form layout
evidence:

```text
41c4fa5e7368a3ae94b60e8a0071c9e575033a4db54682311cde734136f1e751  p9-02-long-two-speakers-polish_results.json
d7cec53344de5b60b005ce12f5362bee1e4dc29bba7f07c8877853f3728e0ad1  p9-02-long-two-speakers-polish_subtitles_v004.srt
ef8f0050fe7e1c95e8f13fc9fa8f7d497dd575920e476a021d4c60ae6464467f  p9-02-long-two-speakers-polish_subtitles_v004.vtt
```

This closes text splitting for the MVP. The remaining long-form activity is a separate
YouTube Studio timing check; it must not reopen layout unless the platform reveals an
actual serialization defect.

The private YouTube Studio timing review passed on the complete 34.7-minute P9-02 sample,
both at normal playback speed and at 2×. The generated review MP4 used H.264 video and AAC
audio and had duration 2083.613 seconds. Timing evidence:

```text
9cc87af0d7ebb27555be7802580fea08cc7d18d602f2d1bd42005c378272850d  p9-02-youtube-timing.mp4
d7cec53344de5b60b005ce12f5362bee1e4dc29bba7f07c8877853f3728e0ad1  p9-02-long-two-speakers-polish_subtitles_v004.srt
```

Minor lexical transcription errors were observed but do not affect subtitle layout,
serialization, or timing acceptance. They remain input for the planned Version 2
versioned transcript-correction workflow.

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
