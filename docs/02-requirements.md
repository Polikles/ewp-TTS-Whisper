# Requirements

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Functional requirements

### A. Input and discovery

- **FR-A01** The application MUST accept a path to a single file or a directory.
- **FR-A02** For a directory, the application MUST inspect only files directly inside that directory by defaultA
- **FR-A03** Recursive discovery MUST require an explicit option.
- **FR-A04** The application MUST identify media content through FFmpeg/ffprobe rather than relying only on filenamA extensions.
- **FR-A05** The application MUST support audio files and extraction of a selected audio stream from video files.
- **FR-A06** When multiple audio streams exist, the application MUST require a selection. In non-intAractive mode, a missing selection is an error for that file.
- **FR-A07** The application MUST normalize Windows and WSL paths.
- **FR-A08** The application MUST NOT follow symbolic links by default.
- **FR-A08.1** No, --force nor any other command MUST NOT make symlink to be followed.
- **FR-A08.2** Symlinks found during batch processing MUST be omitted and result in warning. 
- **FR-A08.3** Symlinks pointing to one singular file MUST result in error.

### B. Episode grouping

- **FR-B00** The application MUST group files that share a base name and have a speaker suffix separated by the final hyphen, e.g. `S01E01_audio-john.mp3` recognizes `john` as the speaker name.
- **FR-B01** A speaker suffix in a single filename MUST be interpreted only when `speaker_count = 1`.
- **FR-B02** In `speaker_count = auto` mode or when the value is not 1, the suffix of a single file MUST NOT be used as a speaker label.
- **FR-B03** An unsuffixed base file and one or more suffixed files MAY form a group; the base file receives a default speaker label.
- **FR-B04** An explicitly supplied group MUST take precedence over automatic grouping.
- **FR-B05** Files in a group MUST have the same sample rate.
- **FR-B06** A duration difference of up to 100 ms is accepted, a difference above 100 ms produces a warning, and a difference above 500 ms blocks the group.
- **FR-B07** Bypassing the duration block MUST require a separate option; `--force` MUST NOT bypass it.

### C. Channels and speakers

- **FR-C00** The application MUST classify input as `mono`, `dual_mono`, `split_speakers`, `mixed_stereo`, or `ambiguous`.
- **FR-C01** Identical or nearly identical channels MUST be treated as one channel containing one or more speakers.
- **FR-C02** Confidently detected `split_speakers` input MUST be transcribed per channel without conventional diarization.
- **FR-C03** Ambiguous stereo MUST produce a warning and use one channel.
- **FR-C04** The user MUST be able to override `channel_mode`.
- **FR-C05** Speaker count MUST be optional and accept `auto` or a positive integer.
- **FR-C06** For `speaker_count = 1`, the application SHOULD skip diarization.
- **FR-C07** For separate files or split channels, each file/channel MUST represent one speaker.
- **FR-C08** Speaker-label priority MUST be: explicit parameter, filename, semantic track/channel metadata, then `SpeakerN`.
- **FR-C09** `Speaker1` MUST mean the first speaker encountered chronologically, independently of backend-specific identifiers.

### D. Transcription

- **FR-D00** The default language MUST be `pl`.
- **FR-D01** The application MUST support explicit `pl`, `en`, and `auto` language modes.
- **FR-D02** The MVP MUST NOT switch language or alignment model within a recording.
- **FR-D03** The application MUST generate transcription, word alignment, and diarization when required.
- **FR-D04** A missing word timestamp MUST NOT fail the entire job.
- **FR-D05** The source of every word timestamp MUST be recorded as `aligned`, `interpolated`, or `segment_fallback`.
- **FR-D06** Overlapping speech MUST be represented in JSON even when the second speaker's words cannot be reconstructed reliably.
- **FR-D07** The canonical transcript MUST preserve meaningful repetitions, self-corrections, and faithful wording; it MUST NOT be paraphrased by an LLM.

### E. Results and exports

- **FR-E00** Every completed job MUST create a schema-valid `results.json`.
- **FR-E01** `segments.json` MUST be an optional export derived from `results.json`.
- **FR-E02** TXT MUST contain no timestamps, use one sentence per line, and group text by speaker.
- **FR-E03** SRT and VTT MUST be segmented using readability rules rather than raw backend segments.
- **FR-E04** Speaker labels in subtitles MUST appear at the first occurrence and after each speaker change.
- **FR-E05** For a single speaker, labels MUST be omitted by default.
- **FR-E06** TXT, SRT, VTT, and `segments.json` MUST be regeneratable without running ASR again.
- **FR-E07** All timestamps in JSON MUST be integer milliseconds.
- **FR-E08** All text formats MUST use UTF-8.

### F. Duplicates, versions, and state

- **FR-F00** The application MUST calculate SHA-256 for every source before transcription.
- **FR-F01** A grouped episode MUST receive a deterministic `episode_signature` that includes hashes, speaker assignments, channel selections, and stream selections.
- **FR-F02** A completed result with the same signature MUST be skipped unless `--force` is supplied.
- **FR-F03** `--force` MUST create the first available `_vNNN` suffix, beginning with `_v002`.
- **FR-F04** All exports created during one run MUST use the same version number.
- **FR-F05** A source with the same name but a different signature MUST create a new version without overwriting existing files.
- **FR-F06** The final `_results.json` MUST be created only after successful completion.
- **FR-F07** In-progress and failed runs MUST use `.partial.json` and `.failed.json` files.
- **FR-F08** An incomplete file MUST be processed again from the beginning.
- **FR-F09** Failure of one job MUST NOT stop the remaining batch.

### G. CLI operations

- **FR-G00** `inspect` MUST analyze input without loading ASR models.
- **FR-G01** `dry-run` MUST show groups, decisions, skipped jobs, warnings, and planned outputs.
- **FR-G02** `transcribe` MUST execute the complete pipeline.
- **FR-G03** `export` MUST operate only on an existing JSON result.
- **FR-G04** `doctor` MUST verify the environment, CUDA, FFmpeg, and models without exposing secrets.
- **FR-G05** `clean` MUST remove only explicitly selected working files.
- **FR-G06** The application MUST provide a non-interactive mode with no prompts.

### H. Models and offline operation

- **FR-H00** Application installation MUST NOT automatically download gated models.
- **FR-H01** A missing required model MUST produce a clear error and setup instructions.
- **FR-H02** The Hugging Face token MUST be read from the `HF_TOKEN` environment variable.
- **FR-H03** After models have been prepared locally, transcription MUST work without network access.

## 2. Non-functional requirements

- **NFR-001 Privacy:** the pipeline performs no upload of audio or transcript text - everything is processed locally.
- **NFR-002 Reproducibility:** dependencies use a lockfile, and the effective configuration is stored in JSON.
- **NFR-003 Stability:** a 60-minute file must complete without OOM on an RTX 3090 using the `accurate` preset.
- **NFR-004 Atomicity:** the application must not leave a final result with an incomplete status.
- **NFR-005 Operational determinism:** identical sources and configuration must produce identical grouping, versioning, and export decisions.
- **NFR-006 Extensibility:** the core must be independent of the CLI and reusable by a future GUI.
- **NFR-007 Testability:** FFmpeg, ASR, alignment, and diarization adapters must support test doubles.
- **NFR-008 Observability:** structured logs, warning codes, batch summaries, and time/VRAM metrics are required.
- **NFR-009 Security:** tokens MUST NEVER appear in logs, JSON, or exception output.
- **NFR-010 Path compatibility:** Unicode, spaces, and Windows/WSL path forms must be supported.
- **NFR-011 Non-destructive behavior:** source files and existing results must not be deleted or overwritten.
- **NFR-012 Documentation and compatibility:** a JSON schema change requires a `schema_version` update and either migration support or a compatible reader.
