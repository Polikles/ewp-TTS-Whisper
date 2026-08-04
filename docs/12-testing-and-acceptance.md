# Testing and Acceptance Criteria

Tests are divided into two matrices: application behavior and audio-material types.

## 1. Application tests

### Discovery and paths

- [ ] Single Windows path with backslashes.
- [ ] Windows path with forward slashes.
- [ ] `/mnt/d` path.
- [ ] Spaces, Polish characters, and general Unicode.
- [ ] Directory without recursion.
- [ ] Explicit recursion.
- [ ] Symbolic link skipped by default.
- [ ] File with a misleading extension detected by content.

### Grouping

- [ ] `S01E01-jan` + `S01E01-anna`.
- [ ] Base identifier containing underscores.
- [ ] Single hyphenated file with `speaker_count=auto`.
- [ ] Single hyphenated file with `speaker_count=1`.
- [ ] Base file plus suffixed file.
- [ ] Ambiguous names are not grouped.
- [ ] Explicit group overrides automatic detection.

### Timeline validation

- [ ] Difference of 0 ms.
- [ ] Difference of 100 ms.
- [ ] Difference of 101 ms produces a warning.
- [ ] Difference of 500 ms produces a warning.
- [ ] Difference of 501 ms blocks the group.
- [ ] `--allow-duration-mismatch`.
- [ ] Different sample rates block the group.

### Channels

- [ ] Mono.
- [ ] Identical dual mono.
- [ ] Nearly identical dual mono.
- [ ] Split speakers.
- [ ] Mixed stereo.
- [ ] Ambiguous input uses one channel and emits a warning.
- [ ] Forced channel mode.
- [ ] An implausible forced mode produces a visible warning.

### Hashing and versioning

- [ ] Same SHA and same name results in SKIP.
- [ ] Same SHA and different name results in SKIP.
- [ ] Same SHA with `--force` creates `_v002`.
- [ ] Existing `_v002` causes `_v003` allocation.
- [ ] Same name with different SHA creates a new version.
- [ ] A grouped signature changes when one source changes.
- [ ] Every export in a run uses the same version.
- [ ] Concurrent version allocation does not collide.

### State and failures

- [ ] SIGINT during ASR.
- [ ] Exception during alignment.
- [ ] Exception during diarization.
- [ ] Disk full.
- [ ] Output write error.
- [ ] Corrupt partial result.
- [ ] Restart processes the file from the beginning.
- [ ] One failed job does not stop the batch.
- [ ] Temporary files are preserved after failure.
- [ ] Temporary files are removed after success.
- [ ] `--keep-temp`.
- [ ] `clean --dry-run`.

### JSON

- [ ] Conformance to JSON Schema.
- [ ] `schema_version` and `application_version` present.
- [ ] Monotonic timestamps.
- [ ] No secrets.
- [ ] Complete effective-configuration snapshot.
- [ ] Correct `timestamp_source` values.
- [ ] Overlap and active-speaker metadata.
- [ ] Final JSON exists only for `completed` status.

### Exports

- [ ] TXT contains no timestamps.
- [ ] One sentence per line.
- [ ] Speaker blocks.
- [ ] No label for a single speaker.
- [ ] SRT is syntactically valid.
- [ ] VTT is syntactically valid.
- [ ] No more than two lines per cue.
- [ ] `on-change` labels.
- [ ] Regeneration without source audio.
- [ ] Optional `segments.json`.
- [ ] Fast speech does not create unintended overlapping cues.

### Environment

- [ ] `doctor` without a GPU.
- [ ] `doctor` with RTX 3090.
- [ ] Missing FFmpeg.
- [ ] Missing model.
- [ ] Missing `HF_TOKEN` before model download.
- [ ] Complete offline readiness.
- [ ] Token is not written to logs.

### Performance and resources

- [x] A 60-minute file completes without OOM on RTX 3090.
- [x] Peak VRAM is recorded or marked unavailable.
- [x] Stage timings are recorded.
- [x] VRAM usage does not grow across consecutive batch jobs.
- [x] Ten sequential files complete without stability degradation.

## 2. Audio-material matrix

- [ ] Clean Polish podcast, one speaker.
- [ ] Polish podcast, two speakers mixed to mono.
- [ ] Polish material with three speakers.
- [ ] Polish speech with English technical terms.
- [ ] Full English recording.
- [ ] Split-speaker stereo.
- [ ] Audacity dual mono.
- [ ] Two separate mono files.
- [ ] Overlap on separate tracks.
- [ ] Overlap in mixed mono.
- [ ] Fast speech.
- [ ] Long pauses.
- [ ] Intro/outro music.
- [ ] Light recorder noise.
- [ ] Clipping.
- [ ] Unequal channel levels.
- [ ] WAV 44.1 kHz.
- [ ] WAV 48 kHz.
- [ ] MP3.
- [ ] FLAC.
- [ ] M4A/AAC.
- [ ] Opus.

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
