# Testing and Acceptance Criteria

Tests are divided into two matrices: application behavior and audio-material types.

Checked application items may be satisfied by deterministic automated tests, recorded WSL
integration gates, or both. Hardware-, player-, and corpus-dependent items remain open until
their corresponding external evidence is accepted.

## 1. Application tests

### Discovery and paths

- [x] Single Windows path with backslashes.
- [x] Windows path with forward slashes.
- [x] `/mnt/d` path.
- [x] Spaces, Polish characters, and general Unicode.
- [x] Directory without recursion.
- [x] Explicit recursion.
- [x] Symbolic link skipped by default.
- [x] File with a misleading extension detected by content.

### Grouping

- [x] `S01E01-jan` + `S01E01-anna`.
- [x] Base identifier containing underscores.
- [x] Single hyphenated file with `speaker_count=auto`.
- [x] Single hyphenated file with `speaker_count=1`.
- [x] Base file plus suffixed file.
- [x] Ambiguous names are not grouped.
- [x] Explicit group overrides automatic detection.

### Timeline validation

- [x] Difference of 0 ms.
- [x] Difference of 100 ms.
- [x] Difference of 101 ms produces a warning.
- [x] Difference of 500 ms produces a warning.
- [x] Difference of 501 ms blocks the group.
- [x] `--allow-duration-mismatch`.
- [x] Different sample rates block the group.

### Channels

- [x] Mono.
- [x] Identical dual mono.
- [x] Nearly identical dual mono.
- [x] Split speakers.
- [x] Mixed stereo.
- [x] Ambiguous input uses one channel and emits a warning.
- [x] Forced channel mode.
- [x] An implausible forced mode produces a visible warning.

### Hashing and versioning

- [x] Same SHA and same name results in SKIP.
- [x] Same SHA and different name results in SKIP.
- [x] Same SHA with `--force` creates `_v002`.
- [x] Existing `_v002` causes `_v003` allocation.
- [x] Same name with different SHA creates a new version.
- [x] A grouped signature changes when one source changes.
- [x] Every export in a run uses the same version.
- [x] Concurrent version allocation does not collide.

### State and failures

- [x] SIGINT during ASR.
- [ ] Exception during alignment.
- [ ] Exception during diarization.
- [ ] Disk full.
- [ ] Output write error.
- [ ] Corrupt partial result.
- [x] Restart processes the file from the beginning.
- [x] One failed job does not stop the batch.
- [x] Temporary files are preserved after failure.
- [x] Temporary files are removed after success.
- [ ] `--keep-temp`.
- [x] `clean --dry-run`.

### JSON

- [x] Conformance to JSON Schema.
- [x] `schema_version` and `application_version` present.
- [x] Monotonic timestamps.
- [x] No secrets.
- [x] Complete effective-configuration snapshot.
- [x] Correct `timestamp_source` values.
- [x] Overlap and active-speaker metadata.
- [x] Final JSON exists only for `completed` status.

### Exports

- [x] TXT contains no timestamps.
- [x] One sentence per line.
- [x] Speaker blocks.
- [x] No label for a single speaker.
- [x] SRT is syntactically valid.
- [x] VTT is syntactically valid.
- [x] No more than two lines per cue.
- [x] `on-change` labels.
- [x] Regeneration without source audio.
- [x] Optional `segments.json`.
- [x] Fast speech does not create unintended overlapping cues.

### Environment

- [x] `doctor` without a GPU.
- [x] `doctor` with RTX 3090.
- [ ] Missing FFmpeg.
- [x] Missing model.
- [ ] Missing `HF_TOKEN` before model download.
- [x] Complete offline readiness.
- [x] Token is not written to logs.

### Performance and resources

- [x] A 60-minute file completes without OOM on RTX 3090.
- [x] Peak VRAM is recorded or marked unavailable.
- [x] Stage timings are recorded.
- [x] VRAM usage does not grow across consecutive batch jobs.
- [x] Ten sequential files complete without stability degradation.

## 2. Audio-material matrix

- [x] Clean Polish podcast, one speaker.
- [x] Polish podcast, two speakers mixed to mono.
- [ ] Polish material with three speakers.
- [ ] Polish speech with English technical terms.
- [ ] Full English recording.
- [x] Split-speaker stereo.
- [x] Audacity dual mono.
- [x] Two separate mono files.
- [x] Overlap on separate tracks.
- [x] Overlap in mixed mono.
- [ ] Fast speech.
- [x] Long pauses.
- [ ] Intro/outro music.
- [ ] Light recorder noise.
- [x] Clipping.
- [x] Unequal channel levels.
- [x] WAV 44.1 kHz.
- [x] WAV 48 kHz.
- [x] MP3.
- [x] FLAC.
- [x] M4A/AAC.
- [x] Opus.

## 3. Text-quality evaluation

### Ground truth

Every representative sample must have a manually verified reference transcript.

Procedure:

1. Select 5–15 minutes from each material type.
2. Produce a manually verified reference transcript.
3. Define one normalization policy for numbers, capitalization, punctuation, and fillers.
4. Run the local pipeline.
5. Optionally run a recognized online model.
6. Compare both systems independently against the same ground truth.
7. Calculate WER and CER.
8. Manually assess proper names, numbers, technical terminology, and English insertions.

### Regression criterion

After the first baseline is approved, no dependency or parameter change may worsen mean WER by more than one percentage point without an explicit project decision.

## 4. Timestamp evaluation

On a manually aligned subset, measure:

- word-start MAE;
- word-end MAE;
- P50, P90, and P95 error;
- percentage of words without alignment;
- number of cues that cut through words incorrectly.

Initial absolute thresholds are set after the reference corpus exists. The release gate requires no regression against the approved baseline.

## 5. Diarization evaluation

Measure separately:

- DER/JER for mixed mono;
- source-based speaker assignment for separate files/channels, expected to be 100%;
- correctness of normalized `SpeakerN` numbering;
- overlap errors.

## 6. Subtitle review

Perform a manual review in the target player or a private YouTube upload:

- readability;
- no excessively long lines;
- speaker labels;
- timing;
- fast speech;
- speaker transitions;
- Polish characters.
