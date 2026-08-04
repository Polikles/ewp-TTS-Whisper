# ADR-0003: Conservative Channel Classification

- Status: accepted
- Date: 2026-07-29
- Last evidence update: 2026-08-03

## Decision

- confident dual mono → use one channel;
- confident split speakers → process channels separately;
- confident mixed stereo → create one working downmix;
- ambiguous stereo → warn and use one channel;
- the user may override the mode.

## Rationale

Aggressively transcribing both channels and deduplicating text could remove legitimate repetitions and increase processing cost.

## Consequences

Advanced cross-channel deduplication is deferred to version 2.

## Phase 2 calibration evidence

The initial four-case report and supplementary P2-03 measurement use `ewp-phase2-channel-metrics-v1`, decoded at 16 kHz with 500 ms activity windows. The initial report SHA-256 is:

```text
9afe3e7306ef0436b754a047846da27f9f289904ff29d653080edf11627c3426
```

| Fixture | Intended/known topology | Correlation | Normalized difference | Left only | Right only | Both active |
|---|---|---:|---:|---:|---:|---:|
| P0-01 | true mono | 1.00000000 | 0.000000 | 0.00% | 0.00% | 98.43% |
| P0-04 | lossy near-identical dual mono | 0.99999485 | 0.003210 | 0.00% | 0.00% | 94.82% |
| P2-01 | split speakers | -0.00034489 | 1.366208 | 53.68% | 40.70% | 3.86% |
| P2-02 | submitted as mixed stereo | 0.99999934 | 0.001151 | 0.00% | 0.00% | 95.24% |
| P2-03 | mixed stereo, speakers panned ±30% | 0.57171925 | 0.841335 | 0.47% | 0.47% | 97.63% |

P2-01 supports the activity metric: 3.86% both-active windows correspond to approximately 5.5 seconds, close to the annotated six-second overlap.

P2-02 does not supply mixed-stereo evidence. Its channels are measurably more alike than the accepted lossy dual-mono control P0-04, including a channel RMS difference of only `0.000043 dB`. It must therefore be treated as another near-identical dual-mono fixture unless a later source-level inspection proves a measurement defect.

P2-03 supplies the missing mixed-stereo evidence. Both speakers remain present in both channels, while moderate opposite panning produces a clear waveform difference and almost no exclusive-channel activity. Its audio SHA-256 is `c93657e1501e293f72ef8d18e1042dfe574fc66ebca5020152dc3470f7fac27e`.

## Provisional thresholds

Automatic classification is evaluated in this order:

1. one original channel → `mono`;
2. `dual-mono` when correlation is at least `0.995`, channel RMS difference is at most `1.5 dB`, and normalized difference is at most `0.1`;
3. `split-speakers` when correlation is at most `0.5`, each exclusive-channel ratio is at least `0.05`, and their sum is at least `0.5`;
4. `mixed-stereo` when both-active ratio is at least `0.8` and normalized difference is at least `0.1`;
5. otherwise → `ambiguous`, warn, and use one channel.

Forced modes remain visible and produce a warning when structurally implausible. These thresholds are accepted only as a conservative MVP baseline. The calibration corpus contains one confirmed split-speaker case, one confirmed mixed-stereo case, two effective dual-mono cases, and one structural mono case. Recalibration on the future larger dataset is mandatory.

## Integrated production validation

On 2026-08-03, commit `1ac0f1d` passed the complete target-WSL gate through the
production `transcriber inspect` command. The locked environment remained compatible,
all 69 repository tests passed, and the worktree remained clean. The five fixtures were
classified as follows:

| Fixture | Detected | Processing |
|---|---|---|
| P0-01 | `mono` | `mono` |
| P0-04 | `dual-mono` | `dual-mono` |
| P2-01 | `split-speakers` | `split-speakers` |
| P2-02 | `dual-mono` | `dual-mono` |
| P2-03 | `mixed-stereo` | `mixed-stereo` |

The human-readable P2-01 report also exposed the expected split-speaker decision. The
P2-03 report generated with Hugging Face and Transformers offline controls was
byte-for-byte identical to the normal report. This confirms that production inspection
uses only local media inspection and channel analysis, without model access.

External JSON report hashes:

```text
ebea4d78404b4ced1b6e5d0f953a731694053d1c8147a64c437b296734757c57  p0-01-single-short.inspect.json
0b6f7d857f9a57b4c3fbdd7529c3361a5a69f497e232fd7ce76a290c220ad81e  p0-04-two-speakers-dual-mono.inspect.json
a551f61ae4f361e28af93abb5562c566ad78a6f8716285150d4d270669bc2654  p2-01-split-speakers.inspect.json
46c8805854d2bbc2bb1f4f75e65fe3140894c6998e7bd5a3ec11f2d2e6d6f1d9  p2-02-mixed-stereo.inspect.json
fc274ce32bb3d98f97018a17251893cd7c05aadab0d2fc013c632d4ec35d78d6  p2-03-mixed-stereo.inspect.json
fc274ce32bb3d98f97018a17251893cd7c05aadab0d2fc013c632d4ec35d78d6  p2-03-mixed-stereo.offline.inspect.json
```

The reports stay in the external test-data workspace because they contain absolute local
paths and fixture-derived metadata. Their hashes, decisions, and provenance are retained
here as the repository decision record.

## Phase 7 source-speaker production evidence

On 2026-08-04, P2-01 was processed in two equivalent forms on the target WSL workstation:

- the original stereo file was automatically classified as `split-speakers` and mapped
  to two channel streams from one canonical source;
- lossless left/right mono extractions were grouped by filename as one `p7-group` episode
  with two canonical sources labelled `Left` and `Right`.

The original and copied P2-01 files both had SHA-256
`868542600305d4cb7514b45130ec67e2cab94bc817e9fa9f6db451c0b999a0a3`.
The derived 44.1 kHz mono PCM fixtures were exactly 142.442086 seconds long:

```text
87b13d0226a27a112c0211483eab1c05dab259c22bc737c1bbc880883d1b6d1c  p7-group-Left.wav
69471eaad337d9eed36ac0f179fa889e05f58236c5b7181ccbe11b118d0b4886  p7-group-Right.wav
```

Both production results contained two stable speakers, 18 segments, and 314 words. Both
represented the known simultaneous-speech region with overlap and two active speaker IDs.
The split case used `split_channels` with one physical source; the grouped case used
`file_group` with two physical sources. Neither result loaded or recorded a diarization
model, and no cross-channel text deduplication was applied. The grouped mono tracks
correctly emitted warning-only `AUDIO_HIGH_SILENCE_RATIO` because each isolated speaker
track contains the other speaker's long inactive period.

This accepts the Phase 7 policy: confident split speakers and grouped one-speaker sources
are transcribed independently and composed chronologically without diarization. The
calibration remains small and must be revisited against the future larger dataset.
