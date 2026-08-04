# ADR-0009: Long-duration operational baseline

- Status: accepted
- Date: 2026-08-04

## Decision

The accurate preset is accepted for MVP long-form processing on the reference RTX 3090
WSL2 workstation. The production pipeline completed realistic Polish recordings from
about 21.5 minutes through 151 minutes without CUDA OOM, unbounded process-memory
growth, output corruption, network access, or retained workspaces.

The current operational baseline is:

| Case | Content | Audio duration | Wall time | Real-time speed | Peak process RAM | Sampled peak VRAM |
|---|---|---:|---:|---:|---:|---:|
| P9-01 | mono, one speaker, long silence | 1296.477 s | 60.32 s | 21.49x | 3.87 GiB | 9418 MiB |
| P9-02 | dual mono, two speakers | 2083.656 s | 193.47 s | 10.77x | 3.87 GiB | 14746 MiB |
| P9-03 | dual mono, two speakers | 3009.768 s | 264.20 s | 11.39x | 3.87 GiB | 14149 MiB |
| P9-04 | mono, two speakers, six concatenated episodes | 9103.656 s | 985.27 s | 9.24x | 4.14 GiB | 14602 MiB |

Real-time speed is audio duration divided by measured wall-clock duration. VRAM values
are absolute one-second `nvidia-smi` samples and therefore include the workstation's
pre-existing desktop GPU allocation; they are not application-only allocations.

These values are the first accurate-preset operational baseline. Future preset and
hardware comparisons must also retain wall time, real-time factor, per-stage duration,
peak process RAM, sampled peak VRAM, dependency provenance, and input hashes.

## Evidence

Commit `8bf1ec2` or later passed compatibility checks, formatting, linting, strict
typing, and all 231 automated tests on Ubuntu 24.04 under WSL2. `HF_TOKEN` was absent,
and every measured transcription ran with Hugging Face Hub and Transformers offline.

All four cases:

- exited successfully and produced canonical JSON plus TXT, SRT, and VTT;
- validated against the authoritative canonical schema;
- produced non-empty segments and aligned words;
- skipped the canonical result and all exports on duplicate replay;
- left no application workdir, temporary output, or repository change;
- emitted only dependency warnings already accepted in earlier GPU gates.

Result summary:

| Case | Speakers | Segments | Words |
|---|---:|---:|---:|
| P9-01 | 1 | 88 | 1368 |
| P9-02 | 2 | 297 | 4502 |
| P9-03 | 2 | 388 | 7216 |
| P9-04 | 2 | 1272 | 20174 |

Input hashes:

```text
1410be4e07683079de812481ac1829d01d29e0aab185b656d0f2f989c8d34708  p9-01-long-single-polish.wav
65c25d859864720bef791cf740d0d41caac3411d38d4c4145a9cefc651823030  p9-02-long-two-speakers-polish.mp3
8039ac3b9b9e09491639dea73eae5a6f70f3beebaeb042a304666ed9606d9869  p9-03-long-two-speakers-polish.mp3
35ac2e07454a03d08cf8631219a6aa99454eb3442d2f83db52008dba606db267  p9-04-endurance-two-speakers-polish.mp3
```

External canonical-result hashes:

```text
8c58bc324625a7037b522aac74b4413020c7a2910347d193961685b0cee8ee97  p9-01-long-single-polish_results.json
41c4fa5e7368a3ae94b60e8a0071c9e575033a4db54682311cde734136f1e751  p9-02-long-two-speakers-polish_results.json
73a93c1e4a190db61f99239ca76022733d4e6707a2acb3ec7f3feffd7b11a040  p9-03-long-two-speakers-polish_results.json
c7b0f1a89fc14f58f6e09b440bfea6f9e52597896847c0f0b7a572dec6293151  p9-04-endurance-two-speakers-polish_results.json
```

## Manual review

The recording owner reviewed the generated transcripts locally:

- P9-01 contained no invented speech during its long silent periods;
- P9-02 and P9-03 had stable and, for these cases, flawless diarization;
- P9-04 contained no false speech at concatenated episode boundaries;
- when the same normalized speaker label ended one episode and began the next, adjacent
  transcript text could be joined across the silent boundary; this is expected because
  the canonical input contains no episode-boundary metadata;
- transcripts were near-perfect overall, with small lexical errors and some proper
  names rendered phonetically, for example `Morawek` instead of `Moravec`.

The review did not create timestamped ground truth and is not a WER, CER, DER, or timing
accuracy measurement.

## Consequences and limits

The MVP can claim demonstrated long-form stability through 151 minutes on the reference
workstation and these four inputs. The evidence does not establish a universal maximum
duration, performance on lower-memory GPUs, English alignment quality, or general
accuracy across speakers and recording conditions.

Concatenated files are treated as one continuous episode. Future multi-episode ingest
may preserve explicit boundaries, but boundary-aware segmentation is not required for
the MVP. Proper-name correction remains suitable for later terminology or LLM
post-processing and must not silently alter canonical timestamps.
