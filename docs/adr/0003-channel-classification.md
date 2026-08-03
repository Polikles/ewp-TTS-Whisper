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
