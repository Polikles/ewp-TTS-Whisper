# ADR-0015: Accept the MVP input format matrix

- Status: accepted
- Date: 2026-08-05

## Decision

The MVP accepts WAV, MP3, FLAC, M4A/AAC, and Ogg/Opus audio through the same inspection,
normalization, transcription, canonical-result, export, duplicate-detection, and cleanup
workflow. Format conversion is not an application repair operation: FFmpeg decodes the
source into private working audio, while the original input remains unchanged.

## Evidence

Commit `b4e37e5` or later passed all 254 automated tests. The Ubuntu 24.04 WSL2 RTX 3090
workstation then executed
[`RUN_RELEASE_FORMAT_MATRIX.md`](../../archive/mvp-validation-runbooks/RUN_RELEASE_FORMAT_MATRIX.md).
Three fixtures were derived from the verified 95.376-second mono P0-01 source:

```text
c6911158a46a76f822dcb78c3d93a1a886db64358822464d6505d98436dd9cc6  flac_sample.flac
e55203e4d0f4ecf64d75a81834faa097bea3f422e7733ea6f52caeef12b778cd  m4a_sample.m4a
df80c762e151ae6308a4028c4a7147963d7d2da5e175addc5ac2c9ebbb5f2e29  opus_sample.opus
```

FFprobe identified FLAC, AAC in an M4A/MP4 container, and Opus in an Ogg container. All
were mono at 48 kHz and approximately 95.38 seconds. Inspection found three independent
mono jobs. Each completed result contained 13 segments and 226 words, and each produced
TXT, SRT, and VTT exports. The three normalized transcripts were byte-identical:

```text
127eea14b247d8a6c6b32cf79c82ae7159a69ddfd964e4b5b2a1e9521eca9e1b
```

Accepted canonical-result hashes:

```text
293045fab607ee309ddf19152309eddfb6976affcd16992bcb1c9d30cc3fb0db  flac_sample_results.json
9a7fa8aa4236f76923739b539a7c3bb2c268628dab85e2d4ef1ef2084d4bbb6a  m4a_sample_results.json
856c53169e2f6f136185eea0052ac1c37820422559b34731cf4dd11d033230c9  opus_sample_results.json
```

The first-run summary was not retained because the operator inadvertently invoked the
command twice. This does not invalidate the gate: the canonical results and complete
exports passed structural validation, and both the accidental second invocation and the
intentional replay reported `completed=0 skipped=3 failed=0 cancelled=0`. No successful
work directory remained.

## Consequences

The advertised audio extensions now have real end-to-end evidence rather than discovery
tests alone. Codec-dependent timestamps can differ slightly—Opus produced different SRT
and VTT hashes—while its normalized transcript remained identical to the lossless and AAC
cases. Future format regressions should reuse this gate and compare structure and lexical
content rather than require byte-identical timed exports across codecs.
