# ADR-0002: Canonical `results.json`

- Status: accepted
- Date: 2026-07-29

## Decision

Every successful run creates a rich `results.json`. TXT, SRT, VTT, and segments JSON are derived exports that do not require source audio.

## Rationale

- no repeated expensive ASR;
- subtitle parameters can be changed later;
- future GUI and dataset projects can reuse the same data;
- reproducibility and diagnostics.

## Consequences

The schema is a public project contract and requires versioning and compatibility tests.

## Phase 4 implementation and validation evidence

On 2026-08-03, the canonical-result and derived-export vertical slice passed on the
target Ubuntu 24.04 WSL2 workstation at commit `9c00f8c`:

- the locked environment resolved 139 packages and passed `uv pip check`;
- formatting, linting, strict typing, and all 150 automated tests passed;
- the checked-in canonical example produced TXT, SRT, VTT, and schema-valid segments
  JSON using only `transcriber export`;
- TXT contained speaker blocks, one sentence per line, and no timestamps;
- SRT and VTT structure, timestamps, and on-change speaker labels passed;
- segments JSON passed the authoritative schema and retained canonical-result
  provenance;
- export succeeded with `CUDA_VISIBLE_DEVICES` empty and Hugging Face/Transformers
  offline controls enabled;
- no source audio, model initialization, download, or token was required;
- no temporary export file remained and the repository worktree was clean.

The controlled external artifact hashes were:

```text
6ab17f931db9037d9ca982f7a111336ae931c1ee6368f2a6bcfb0ba575323b0c  S01E01_results.json
296de1f05a30b7cbe80d3de5f5b319789b542e1f28c1da2f18e9cf5e11de40f6  S01E01_segments.json
0c61b0cdf2ff00dcf63ed254b8e3d686613ad32bfadef2d65aef94abcaac5b1d  S01E01_subtitles.srt
7bb305e38d7a5df65c0ec5c83eb6c4398de3b8d8a8fe7f12cd3eaced7844be58  S01E01_subtitles.vtt
16b0993ded8a17bc1bfc934a6c9ea97b3adc5671e36130e25b643e1674d045e3  S01E01_transcript.txt
```

This gate proves export behavior against the controlled canonical example. Subtitle
tuning against longer live Polish results remains part of later end-to-end phases.

## Phase 5 first production finding

On 2026-08-03, the first P0-01 production run at commit `0a54411` passed the locked
environment, pinned-snapshot, local-only, GPU visibility, ASR, alignment, normalization,
and canonical-publication stages. The accepted Lightning checkpoint-upgrade notice and
TF32 reproducibility warning recurred. No download, token request, CUDA OOM, or ML-stage
error occurred.

The command then failed while deriving subtitles: one live Polish ASR segment had a
total character count within the nominal `max_lines * max_chars_per_line` capacity but
its word boundaries still required more than two lines. This demonstrates that nominal
capacity is not equivalent to a valid wrap. Canonical JSON had already been published,
as required by this ADR, while derived exports remained absent.

The corrective decision is:

- validate chunk candidates using the actual word-wrap constraint, including any
  displayed speaker-label width;
- retain strict line-count and line-length limits by splitting at timed word boundaries;
- on a duplicate completed result, create only missing configured exports without
  rerunning ML or replacing canonical JSON;
- convert remaining rendering `ValueError` failures into a sanitized application error
  instead of exposing a terminal traceback.

### Corrected target result

The corrected target gate passed later on 2026-08-03:

- the existing canonical result validated against the authoritative schema with 13
  segments and 226 completely timestamped, single-speaker words;
- the result recorded the exact accepted ASR and Polish-alignment revisions;
- duplicate recovery generated the three missing exports without loading ML or replacing
  canonical JSON;
- a subsequent duplicate invocation skipped the completed result and all existing
  exports without mutation;
- a forced local-only replay ran ASR and alignment again and consistently published one
  coordinated v2 canonical/TXT/SRT/VTT set;
- v1 and v2 TXT, SRT, and VTT were byte-for-byte identical;
- no partial, failed, or temporary output state remained;
- the marker-verified retained workspace from the original export failure was safely
  removed, both successful workspaces were cleaned, and the repository was clean.

The controlled external artifact hashes were:

```text
d7d5c183c7e7dc6eb85765adbecfad56cab6dada430d7b43ae568ce44cc8478b  p0-01-single-short_results.json
b98ffdc33c66677df50b340803858a71fe2086d3145a05eba9e63718a26abb17  p0-01-single-short_results_v002.json
689dfa9328a8351ae5839773aeb95e76552840f861e4114d00557e623b60cb74  p0-01-single-short_subtitles.srt
b497918dc89cf1cbd72648ce7c6c66bbb194591fc0cc3b4dca398f4a191da6c8  p0-01-single-short_subtitles.vtt
689dfa9328a8351ae5839773aeb95e76552840f861e4114d00557e623b60cb74  p0-01-single-short_subtitles_v002.srt
b497918dc89cf1cbd72648ce7c6c66bbb194591fc0cc3b4dca398f4a191da6c8  p0-01-single-short_subtitles_v002.vtt
127eea14b247d8a6c6b32cf79c82ae7159a69ddfd964e4b5b2a1e9521eca9e1b  p0-01-single-short_transcript.txt
127eea14b247d8a6c6b32cf79c82ae7159a69ddfd964e4b5b2a1e9521eca9e1b  p0-01-single-short_transcript_v002.txt
```

Canonical v1/v2 hashes intentionally differ because run IDs, timestamps, and stage
durations are execution metadata. The matching derived hashes prove deterministic
transcript and subtitle rendering from equivalent inference output.

## Phase 7 multi-speaker export evidence

On 2026-08-04, the first source-speaker target runs at commit `025e56e` completed two
local-only ASR/alignment stream passes per job and published schema-valid canonical JSON.
Derived export rendering then exposed a second canonical-first boundary case: chunks from
one long speaker segment could extend beyond the start of another overlapping speaker
segment, so per-segment emission produced non-monotonic subtitle cue order.

Commit `33060f6` changed subtitle generation to build conservative unlabelled candidates,
sort them on the shared timeline, and only then apply on-change speaker labels. The
existing canonical results recovered TXT, SRT, and VTT without model loading or canonical
replacement. Subsequent duplicate runs skipped every result and export.

Both split-channel and grouped-file canonical results passed the authoritative schema and
contained 18 segments and 314 words, with two deterministic speakers, explicit overlap,
complete source attribution, and only ASR/alignment model provenance. Labelled TXT/SRT/VTT
exports passed. No temporary file remained and the WSL worktree was clean.

External artifact hashes:

```text
eea4031df732216a6807da95ba360383761bc1d5266be93678e9f244d50a6c79  p2-01-split-speakers_results.json
0ff7c83953fe0f5942932ff2a9ef203c1556616949851c76de9bc8ae32f05e4e  p2-01-split-speakers_subtitles.srt
4244cd7b47171351e57bd735e1c086c3d61f8a6ee1b0782dd1ba7e0f58c0f44c  p2-01-split-speakers_subtitles.vtt
25944db0a98edfc1f968aaf0643ef7c0554287c5905cc5f9899765da53feedb0  p2-01-split-speakers_transcript.txt
5090960a4cb4c76e529b2d27669b054ddf2ce02159c3050ec728e53d37165e35  p7-group_results.json
7568b675d1044eab813c012de43acfff0aeb23690675a8073d63f4119fd986da  p7-group_subtitles.srt
5d3b0f63492a5f33276fe504afd8c6731f4109adb1385997c318997869b7129d  p7-group_subtitles.vtt
fa01eec7eba1c041aac83070da10b4521dc383c3caa80919a87ebaa3ac2bea2c  p7-group_transcript.txt
```

The two canonical and derived sets are not expected to have equal hashes: they record
different physical-source topology and labels (`Speaker1`/`Speaker2` versus
`Left`/`Right`). Their equal segment and word counts support equivalent processing of the
same losslessly separated P2-01 timeline.
