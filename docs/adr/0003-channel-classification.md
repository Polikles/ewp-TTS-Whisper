# ADR-0003: Conservative Channel Classification

- Status: accepted
- Date: 2026-07-29
- Last evidence update: 2026-08-03

## Decision

- confident dual mono → use one channel;
- confident split speakers → process channels separately;
- ambiguous stereo → warn and use one channel;
- the user may override the mode.

## Rationale

Aggressively transcribing both channels and deduplicating text could remove legitimate repetitions and increase processing cost.

## Consequences

Advanced cross-channel deduplication is deferred to version 2.

## Phase 2 calibration evidence

The initial four-case report uses `ewp-phase2-channel-metrics-v1`, decoded at 16 kHz with 500 ms activity windows. Report SHA-256:

```text
9afe3e7306ef0436b754a047846da27f9f289904ff29d653080edf11627c3426
```

| Fixture | Intended/known topology | Correlation | Normalized difference | Left only | Right only | Both active |
|---|---|---:|---:|---:|---:|---:|
| P0-01 | true mono | 1.00000000 | 0.000000 | 0.00% | 0.00% | 98.43% |
| P0-04 | lossy near-identical dual mono | 0.99999485 | 0.003210 | 0.00% | 0.00% | 94.82% |
| P2-01 | split speakers | -0.00034489 | 1.366208 | 53.68% | 40.70% | 3.86% |
| P2-02 | submitted as mixed stereo | 0.99999934 | 0.001151 | 0.00% | 0.00% | 95.24% |

P2-01 supports the activity metric: 3.86% both-active windows correspond to approximately 5.5 seconds, close to the annotated six-second overlap.

P2-02 does not supply mixed-stereo evidence. Its channels are measurably more alike than the accepted lossy dual-mono control P0-04, including a channel RMS difference of only `0.000043 dB`. It must therefore be treated as another near-identical dual-mono fixture unless a later source-level inspection proves a measurement defect.

No split-versus-mixed or mixed-versus-ambiguous threshold is accepted from this four-case report. A genuinely different-channel mixed-stereo fixture is still required. All eventual thresholds remain provisional until rerun on the larger dataset.
