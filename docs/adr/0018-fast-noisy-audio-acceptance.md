# ADR-0018: Synthetic fast-speech and recorder-noise acceptance

- Status: accepted
- Date: 2026-08-05

## Context

The representative audio matrix still required fast speech and light recorder noise.
The verified P0-02 Polish single-speaker recording has a manually checked reference, so
it can exercise both conditions while keeping lexical changes measurable.

## Decision

The MVP accepts deterministic derived fixtures as smoke-test evidence for these two
material conditions:

- `fast-polish.wav` applies FFmpeg `atempo=1.6`, preserving pitch while reducing the
  276.170-second source to 172.613 seconds;
- `light-recorder-noise.wav` mixes low-amplitude pink noise into a mono 48 kHz copy while
  retaining the source duration.

This evidence closes the two representative-material rows. It does not add either
derived recording to the lexical corpus baseline and does not define a universal noise
or speaking-rate threshold.

## Evidence

Commit `f1355b4` or later passed all 279 automated tests before the external run.
`HF_TOKEN` was absent and the complete batch ran with model hubs forced offline.

Input and derived-fixture hashes:

```text
32c19ea948404ed0b08d42ce8a03dbcfc4672248ca7b261550a1d4f88f61c46a  p0-02-single-representative.wav
c34adb93956e0c5cd04f2abb7b4172046ee9c8120ed48b82db91c54eda3b672f  p0-02-single-representative.txt
739c25ed73f09b71bbeeff8f4805227cd116f277f226e1d27fad22e5b47c288f  fast-polish.wav
28663775d89eca94df9c92e7795458b2334c0f2917a1137eaeb5ed9fde833a48  light-recorder-noise.wav
```

Both jobs completed with canonical JSON plus TXT, SRT, and VTT. Fast speech produced 32
segments and 602 words; light noise produced 32 segments and 613 words. Normalized
lexical results against the P0-02 reference were:

| Case | WER | CER | Substitutions | Deletions | Insertions |
| --- | ---: | ---: | ---: | ---: | ---: |
| fast speech | 0.02768730 | 0.01370187 | 5 | 12 | 0 |
| light noise | 0.00488599 | 0.00141743 | 2 | 1 | 0 |

The noisy fixture did not degrade the accepted P0-02 lexical result. Accelerated speech
increased errors but remained intelligible and produced no insertions or failure.

Canonical and evidence hashes:

```text
1828eea0c10ef3fb312c28f58dc19470208ed8ad0613bd8649ac1dea14ecee10  fast-polish_results.json
b0ad7af5be1af6b7c0b748b09201278cf375ba3113116480d7d95334e4257b7e  light-recorder-noise_results.json
9ec820ad7b9d53aa0e344c90885a1177c4e90e6788ca54ce6ee3b95de67936b3  fast-polish-quality.json
e4a3a68dcba59c65f8f2935d567814ad1569c7f0943426f33ac49a4a674e1247  inspect.json
dd263a9735184c936d2ae33b1c4458d2bb2f5145c5a943469762212536aee8fd  light-recorder-noise-quality.json
```

Duplicate replay reported two skips, no model work was repeated, and no application
workdir remained.

## Consequences

Future model or preset changes can repeat the same transformations and compare scores.
Broader robustness claims still require naturally fast speech and multiple real recorder
noise profiles in the archive-derived corpus.
