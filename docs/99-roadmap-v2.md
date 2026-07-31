# Version 2 Roadmap

The following items do not block the MVP.

## 1. GUI

- file, directory, and group selection;
- dry-run preview;
- audio-stream selection;
- speaker-label editing;
- warning display;
- job queue;
- popup or secure token storage;
- transcript, speaker, and timestamp editor;
- re-export without ASR.

## 2. Audio repair

- problem-type classification;
- denoising;
- loudness normalization;
- clipping repair where feasible;
- dereverberation;
- creation of a new working file without modifying the source;
- separate SHA-256 for the processed variant;
- `off`, `ask`, and `auto` modes;
- comparison of original and repaired audio.

## 3. Transcript comparison

- transcribe original and repaired audio;
- compare confidence and agreement automatically;
- difference report;
- select the better result or a controlled hybrid;
- preserve both canonical results.

## 4. LLM post-processing

- local LM Studio endpoint;
- cloud API as an explicit option with proper privacy warning;
- punctuation and proper-name correction;
- terminology dictionary;
- filler removal as an export, not a canonical-text mutation;
- strict change tracking;
- no timestamp movement without word mapping;
- optional (with prepared prompts) summaries.

## 5. Presets and benchmark

- `balanced`;
- `low-vram`;
- `cpu`;
- automatic batch-size selection;
- bundled or explicitly downloaded licensed audio samples;
- benchmark of speed, VRAM, WER, timestamps, and diarization;
- HTML/JSON report;
- hardware comparison.

## 6. Advanced channel handling

- detect and remove duplicates caused by crosstalk;
- compare channel transcripts with timestamps;
- preserve legitimate single-word and rhetorical repetitions;
- support for more than two channels in one file.

## 7. Subtitles

- speaker colors;
- styled WebVTT;
- ASS/SSA;
- burned-in subtitles;
- platform presets;
- visual preview.

## 8. Distribution

- GPU-enabled Docker image;
- pinned image versions;
- local service/API;
- GUI installer;
- Ubuntu 26.04 LTS qualification;
- optional native Windows support as Tier 2.

## 9. Operations

- `fail-fast`;
- queue scheduling;
- automatic cleanup of old work directories;
- quality-trend reports between releases.
