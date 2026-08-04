# ADR-0008: Mixed-source speaker diarization

- Status: accepted
- Date: 2026-08-04

## Decision

For one mono, dual-mono, or mixed-stereo source containing multiple speakers,
EWP-transcripts uses the pinned local
`pyannote/speaker-diarization-community-1` snapshot after ASR and word alignment.

- an exact positive speaker count is passed to the backend when supplied;
- `auto` leaves speaker-count estimation to the backend;
- backend clusters are normalized by chronological first appearance to stable public
  labels `Speaker1`, `Speaker2`, and so on;
- regular diarization turns preserve simultaneous active speakers and overlap metadata;
- the exclusive timeline is preferred for deterministic word assignment;
- uncovered or exactly tied words remain unassigned and produce structured warnings;
- source-based split-channel and grouped-file paths remain independent and do not load
  diarization;
- cluster labels are anonymous and are not automatic person recognition.

The accepted model revision is:

```text
pyannote/speaker-diarization-community-1
3533c8cf8e369892e6b79ff1bf80f7b0286a54ee
```

Runtime loads the explicit snapshot directory with network access disabled. A missing or
invalid snapshot is an application error rather than a reason to query Hugging Face.

## Rationale

Mixed recordings do not provide a deterministic source or channel identity for each
speaker. Community-1 supplies both a regular overlapping timeline and an exclusive
timeline suitable for assigning a single speaker to each ASR word. Keeping these two
representations avoids hiding overlap merely to make attribution convenient.

Chronological normalization makes backend-specific cluster names unsuitable as public
identities and prevents their accidental interpretation as recognized people.

## Target validation evidence

On 2026-08-04, commit `d32d9a5` passed the Phase 8 gate on the reference Ubuntu 24.04
WSL2 workstation with an RTX 3090. The locked environment passed compatibility checks,
formatting, linting, strict typing, and all 214 automated tests. `HF_TOKEN` was absent.

Two complementary production cases ran with Hugging Face and Transformers offline:

| Case | Input decision | Count mode | Speakers | Segments | Words | Overlap segments |
|---|---|---|---:|---:|---:|---:|
| P2-03 | `mixed-stereo` | exact `2` | 2 | 16 | 249 | 0 |
| P0-03 | `mono` | `auto` | 2 | 51 | 965 | 11 |

Both results:

- validated against the authoritative canonical schema;
- recorded the accepted ASR, alignment, and diarization revisions;
- normalized identities to `speaker_001`/`Speaker1` and
  `speaker_002`/`Speaker2` in first-seen order;
- assigned words to both speakers and generated labelled TXT, SRT, and VTT;
- completed without a download, token request, traceback, CUDA OOM, or network access;
- skipped the canonical result and every export on duplicate replay without loading
  models;
- left no job workdir or temporary file, and the WSL repository remained clean.

The automatic P0-03 result contained 11 overlapping segments with multiple active
speaker IDs. This confirms that overlap remains visible even though exclusive turns are
used for individual word attribution. The exact P2-03 fixture intentionally contains no
overlap.

The accepted Lightning checkpoint upgrade notice, TF32 reproducibility warning, and
short-window `std()` warning recurred. They did not alter the successful application
state and remain dependency-level diagnostics rather than evidence of a failed job.

Fixture hashes:

```text
c93657e1501e293f72ef8d18e1042dfe574fc66ebca5020152dc3470f7fac27e  p2-03-mixed-stereo.wav
a62e2a771f6a09732541d22834d6be8ea25a486cbd4ab1628a5e7bb9d06076ba  p0-03-two-speakers-mixed-overlap.wav
```

External exact-count artifact hashes:

```text
755405b5c2cf689df13b059d13e399c037bc7588d931d2e75f851defd04ca189  p2-03-mixed-stereo_results.json
3da1957eb55756ab72639d3c3199f02fbbd8839d815e6329458e33dff20865c7  p2-03-mixed-stereo_subtitles.srt
c9db83c148ef389d92f1b19e8b2401981c1a9b483d2fb0aa9761f2c3f05330a5  p2-03-mixed-stereo_subtitles.vtt
4396ca17543265e7045948d250d340d4b2c0a7a123e37d405312a5cc8c0a59ef  p2-03-mixed-stereo_transcript.txt
```

External automatic-count artifact hashes:

```text
486cd22dce81b167a88dac8a8e6ee20218d9e155784ee2e80657f61b00ab846e  p0-03-two-speakers-mixed-overlap_results.json
6d64075be38dc61639724c48ad53ada2b1db45ec0a06d5d9fd18a7a6834d32a0  p0-03-two-speakers-mixed-overlap_subtitles.srt
2b25e8356bd828f87bf0af59a80b6480c458a5dad863684769518f417b5f7a03  p0-03-two-speakers-mixed-overlap_subtitles.vtt
c24702e1f99949873dcdf2df1d5238ef22a4002f08cb5bbeeaa9425898d12cfc  p0-03-two-speakers-mixed-overlap_transcript.txt
```

## Consequences and limits

The gate proves production integration, offline reproducibility, canonical attribution,
and overlap representation on two known fixtures. It does not establish general
diarization accuracy: the corpus is very small and has no speaker-timestamp reference,
so DER and timing quality cannot yet be calculated.

Heavy simultaneous speech may still be omitted or misrecognized by ASR even when the
diarization timeline correctly marks overlap. Phase 9 must evaluate a larger manually
annotated corpus and retain this limitation in user-facing documentation.
