# Post-0.1 Roadmap

The filename is retained for compatibility with existing links. The roadmap now tracks
planned work after the `0.1.x` internal release candidates rather than implying that all
items belong to one monolithic "Version 2" release.

## Current execution order

1. **v0.2.0 manual transcript revisions** — promoted from backlog into the next MVP
   increment and specified normatively in
   [`13-transcript-revisions.md`](13-transcript-revisions.md), ADR-0020, and
   [`21-v0.2.0-transcript-revision-plan.md`](21-v0.2.0-transcript-revision-plan.md).
2. Retain the completed 24-episode corrected corpus privately, outside this repository,
   until every included episode is public and redistribution is appropriate.
3. Automated transcript correction using local/cloud API models, configurable chunking,
   read-only overlap, the same revision engine, and manual revision of model output.
4. Manual translation pipeline and structured translation artifact, using corrected
   transcript by default while retaining an explicit raw/dirty source option.
5. Automated translation using the same source/translation artifact contracts, followed
   by optional manual revision.
6. Synchronized HTML transcript/export and remaining publishing features.
7. Remaining audio, discovery, benchmark, subtitle, distribution, and operations work
   based on observed value and risk.
8. GUI after the planned core functions are stable; GUI reuses application services and
   does not implement a parallel pipeline.

The earlier small production pilot requirement is superseded operationally by the larger
manual-review corpus used to build correction ground truth. Existing accepted v0.1
validation evidence remains valid.

The 24-episode audio and corrected-transcript corpus is complete and is the private
reference benchmark for future ASR model, preset, correction, and translation
comparisons. It must not be committed while any included episode is non-public. Once all
episodes are public, publication in this repository requires a separate licensing,
privacy, size, and repository-distribution review; public availability alone does not
implicitly authorize committing the corpus.

## 1. Manual transcript correction — promoted to v0.2.0

The following is no longer an unscheduled roadmap idea. It is the planned v0.2.0 contract:

- immutable canonical `results.json`;
- versioned full-snapshot revision artifacts linked by base-result SHA-256;
- `EWP-REVIEW 1` human-readable manual correction format;
- stable canonical word anchors and corrected speaker attribution;
- batch `revise prepare` and batch `revise apply`;
- `revise preview` and `apply --no-apply` equivalence;
- external-editor `revise edit`, with successful editor close applying automatically
  unless `--no-apply` is used;
- deterministic anchored token alignment for substitutions, punctuation, sentence
  boundaries, merge/split, insertion, deletion, repetition preservation, and speaker
  reassignment;
- no normal manual timestamp editing;
- runtime `EffectiveTranscript` shared by raw and revised export;
- revision-aware TXT/SRT/VTT/segments regeneration without source audio or ML models;
- mandatory provenance/statistics and optional/reconstructable detailed audit.

Detailed design belongs in docs 13/21 rather than this roadmap.

## 2. Automated transcript correction

Automated correction follows manual correction so model performance can be measured
against manually verified ground truth.

Requirements:

- local API endpoints and explicit cloud API endpoints;
- cloud use is explicit opt-in and requires privacy warnings/documentation;
- no audio is sent to the correction model;
- the LLM receives relevant transcript blocks plus word/speaker/timing metadata needed as
  context, not the complete canonical processing/configuration payload;
- corrected LLM output is passed through the same alignment and `RevisionEngine` used by
  manual review;
- prompt the model to correct only obvious ASR lexical errors, misspelled proper names,
  conservative punctuation, capitalization, and sentence boundaries;
- preserve the speaker's actual wording, repetitions, self-corrections, fillers,
  malformed sentences, grammatical mistakes, and stylistic quirks; never paraphrase,
  polish prose, or silently repair how the person spoke;
- require the provider response to include corrected text plus an explicit proposed
  change list with source span, before/after text, and correction category; the local
  revision engine independently reconstructs the authoritative audit;
- model/prompt/config provenance is persisted without secrets;
- LLM revisions may be direct siblings of manual gold for benchmark comparison;
- a model revision may later have a manual child revision, with parent provenance but a
  complete standalone child snapshot.

### Configurable chunking

Chunking is required for flexibility across local and cloud models and must not assume a
large context window.

Future configuration must expose at least:

- target chunk size;
- maximum chunk size;
- read-only context overlap;
- CLI/request overrides through the normal configuration precedence system.

Exact defaults are deferred until automated-correction benchmarks. Overlap is context
only: every editable source range belongs to exactly one chunk, preventing conflicting
corrections in adjacent requests.

## 3. Optional project-scoped dictionaries

Dictionary support remains conditional on benchmark evidence and is not part of v0.2.0.

If implemented:

- there is no global dictionary;
- users may create/select multiple small named dictionaries scoped to a project, for
  example `podcast`,
  `training`, or `history_lectures`;
- selected terminology may be provided to correction/translation LLMs as context only
  after explicit project/job selection;
- no dictionary is inherited automatically across projects;
- dictionary use is optional, and its identity and content hash must be included in
  provenance where it affects automated output;
- ASR vocabulary biasing is not enabled by default because an irrelevant dictionary may
  reduce recognition quality.

## 4. Manual translation pipeline

Translation is a separate pipeline, not a branch inside transcript correction, although
it reuses common versioning, batch, editor, provenance, audit, and future GUI
infrastructure.

The future translation source can be:

```text
--source raw
```

for an intentionally dirty/raw canonical translation, or a selected corrected revision.
Corrected text is the normal intended production source.

Translation requirements:

- source units are sentence-level after sentenceization of the selected transcript;
- translation mapping is sentence-to-sentence, not word-to-word;
- source sentence timing is retained for target subtitle planning;
- translated word count/order is free to differ from the source language;
- manual translation is implemented first and becomes benchmark ground truth;
- target-language text can itself be manually revised;
- one structured immutable translation artifact becomes the source for target TXT, SRT,
  VTT, and future HTML exports;
- the artifact records exactly which raw result or transcript revision was translated;
- exact translation JSON Schema is deferred until this pipeline is designed.

## 5. Automated translation

After manual translation establishes ground truth:

- add local/cloud API translation providers;
- retain provider/model/prompt/config provenance;
- use configurable chunks/context appropriate to the model;
- preserve sentence-level source mapping and source time spans;
- allow manual revision of automated translations;
- benchmark automated output against manual translations separately from transcript
  correction quality.

Useful benchmark paths include:

```text
raw PL -> automated translation -> compare with EN gold
manual corrected PL -> automated translation -> compare with EN gold
raw PL -> automated correction -> automated translation -> compare with EN gold
```

## 6. Content-aware directory discovery

- Replace the directory extension allowlist with a bounded ffprobe-based candidate
  classifier so any FFmpeg-decodable audio can be included without treating documents,
  cover art, and other ordinary siblings as failed transcription jobs.
- Preserve the current rules for symlinks, recursion, natural ordering, and direct-file
  errors, and emit a structured skip reason for non-audio files.
- Avoid probing each accepted source twice by carrying trusted probe data into inspection.

## 7. Audio repair

- problem-type classification;
- denoising;
- loudness normalization;
- clipping repair where feasible;
- dereverberation;
- creation of a new working file without modifying the source;
- separate SHA-256 for the processed variant;
- `off`, `ask`, and `auto` modes;
- comparison of original and repaired audio.

## 8. Transcript comparison

- transcribe original and repaired audio;
- compare confidence and agreement automatically;
- difference report;
- select the better result or a controlled hybrid;
- preserve both canonical results.

## 9. Presets and benchmark

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

The expanded manual correction corpus should also become the reference source for lexical
correction benchmarks. Separate timestamp and diarization ground truth is still required
for timestamp/DER/JER evaluation.

## 10. Advanced channel handling

This is deferred to V2 or later and is not on the current critical path.

- detect and remove duplicates caused by crosstalk;
- compare channel transcripts with timestamps;
- preserve legitimate single-word and rhetorical repetitions;
- support more than two channels with explicit topology rather than treating channel
  count as speaker count;
- for isolated speaker channels, split selected channels, expose the channel/speaker map
  and warning, transcribe separately, and merge chronological timelines;
- for general multichannel and cinematic 5.1/7.1 audio, use a layout-aware program
  downmix plus diarization and clearly report the transformation;
- automatically use that fallback only for a recognized channel layout; require a
  dedicated explicit `program-mix` topology choice for missing or unsupported layouts,
  and do not overload output-versioning `--force`;
- never silently use one channel as a complete transcription of 3+ channel media.

## 11. Subtitles

- speaker colors;
- styled WebVTT;
- ASS/SSA;
- burned-in subtitles;
- platform presets;
- visual preview.

## 12. Platform transcript delivery and HTML

- qualify SRT and WebVTT behavior on YouTube, Spotify, Apple Podcasts, and selected web
  audio/video players; record account- or host-dependent limitations;
- publish multiple Podcasting 2.0 transcript links where appropriate, including a
  readable transcript and a timed caption resource;
- build an accessible synchronized HTML transcript from the selected effective transcript
  or suitable derived timed data, with sentence-level seeking, current-sentence
  highlighting, and keyboard controls;
- add HTML as an explicit generated export (`transcriber export --format html`), with a
  standalone document and an embeddable fragment that require no transcription rerun;
- apply speaker colors in custom HTML/CSS with textual labels as the portable and
  accessible fallback;
- define export presets for conservative platform interchange and web-native playback;
- design translated/bilingual HTML after the translation artifact contract exists.

## 13. GUI

GUI remains deliberately late in the roadmap so the application/domain contracts are
stable first.

Planned capabilities:

- file, directory, and group selection;
- dry-run preview;
- audio-stream selection;
- warning display and job queue;
- transcript correction and speaker-attribution editing;
- hide review anchors while retaining the same internal revision mapping;
- preview revision changes without applying them;
- re-export raw or selected revision without ASR;
- translation and translated-text revision after those pipelines exist;
- secure handling of optional API credentials;
- audio-following review where useful;
- an About section with application/version information;
- a License section presenting the applicable license and warranty notice;
- a Source Code section with a direct link to the public project repository:
  <https://github.com/Polikles/ewp-transcripts>.

The GUI calls application services directly and MUST NOT execute CLI commands as a
subprocess or maintain a second revision/translation model.

## 14. Distribution

- GPU-enabled Docker image;
- pinned image versions;
- local service/API;
- GUI installer;
- Ubuntu 26.04 LTS qualification;
- optional native Windows support as Tier 2.

## 15. Operations

- `fail-fast`;
- queue scheduling;
- automatic cleanup of old work directories;
- quality-trend reports between releases.

Before the CLI is declared ready for general users, create a top-level `Instructions/`
directory containing a concise operator runbook for every shipped command and workflow:
installation/model preparation, doctor, inspect, dry-run, single/group/batch transcribe,
revision prepare/preview/apply/audit, raw/revised batch export, cleanup, warnings,
recovery, privacy, and command-specific `--help` discovery.
