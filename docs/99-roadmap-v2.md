# Version 2 Roadmap

The following items do not block the MVP.

## Recommended execution agenda

1. Run a bounded internal production pilot on 3–5 representative archive episodes and
   collect structured correction, timing, subtitle, performance, and workflow feedback.
2. Design and implement the versioned correction layer from observed edits, keeping
   canonical ASR results immutable and anchoring corrections to stable words, speakers,
   and timestamps.
3. Regenerate TXT, SRT, VTT, segments JSON, and corrected transcript data atomically
   from one reviewed revision.
4. Add synchronized standalone and embeddable HTML transcript export for the blog audio
   player, including seeking, highlighting, keyboard access, and speaker presentation.
5. Convert licensed manually corrected excerpts into a larger ground-truth corpus, then
   reopen English, three-speaker, timestamp, DER/JER, preset, and hardware gates.
6. Prioritize the remaining roadmap items using pilot frequency, review time saved,
   privacy impact, and implementation risk.

The pilot procedure and minimum feedback summary are documented in
[`../WSL config/FEEDBACK_FOR_V2.md`](../WSL%20config/FEEDBACK_FOR_V2.md).

## Content-aware directory discovery

- Replace the directory extension allowlist with a bounded ffprobe-based candidate
  classifier so any FFmpeg-decodable audio can be included without treating documents,
  cover art, and other ordinary siblings as failed transcription jobs.
- Preserve the current rules for symlinks, recursion, natural ordering, and direct-file
  errors, and emit a structured skip reason for non-audio files.
- Avoid probing each accepted source twice by carrying trusted probe data into inspection.

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

## 4a. Transcript correction and editorial workflow

- keep the original canonical result immutable and store corrections as a versioned
  layer linked by result hash, schema version, and application version;
- represent edits against stable word/time/speaker anchors rather than treating TXT as
  the source of truth;
- import corrected TXT or LLM output through normalized token alignment, automatically
  applying unambiguous substitutions and punctuation while reporting ambiguous
  insertions, deletions, speaker changes, and timestamp mappings for review;
- support punctuation, quotation marks, proper names, sentence boundaries, speaker
  attribution, and explicit split/merge operations with an audit trail;
- record whether each edit was manual, dictionary-driven, or LLM-assisted and preserve
  privacy-relevant processing provenance;
- regenerate TXT, SRT, VTT, segments JSON, and web transcript data atomically from one
  corrected revision; never maintain independent hand-edited exports;
- provide audio-following word or sentence review and re-export without rerunning ASR.

## 5. Presets and benchmark

- `balanced`;
- `low-vram`;
- `cpu`;
- automatic batch-size selection;
- bundled or explicitly downloaded licensed audio samples;
- benchmark of speed, VRAM, WER, timestamps, and diarization;
- repeatable wall-clock, real-time-factor, per-stage duration, peak process RAM, and
  sampled peak VRAM measurements for every preset comparison;
- retain raw measurement provenance so later hardware and dependency baselines can be
  compared without relying on terminal summaries;
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

## 7a. Platform transcript delivery

- qualify SRT and WebVTT behavior on YouTube, Spotify, Apple Podcasts, and selected web
  audio/video players; record account- or host-dependent limitations;
- publish multiple Podcasting 2.0 transcript links where appropriate, including a
  readable transcript and a timed caption resource;
- build an accessible synchronized HTML transcript from canonical/segments JSON, with
  sentence-level seeking, current-sentence highlighting, and keyboard controls;
- add HTML as an explicit generated export (`transcriber export --format html`), with a
  standalone document and an embeddable fragment that require no transcription rerun;
- apply speaker colors in custom HTML/CSS with textual labels as the portable and
  accessible fallback;
- define export presets for conservative platform interchange and web-native playback.

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
