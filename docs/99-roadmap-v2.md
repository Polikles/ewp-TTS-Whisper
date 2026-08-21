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
3. **v0.3 automated transcript correction** using local/cloud API models, configurable
   chunking, read-only overlap, the same revision engine, benchmarking against the
   private corpus, and manual revision of model output. v0.3 also includes the scoped
   fresh-install/verification script and README onboarding work in section 14.
4. **v0.4 manual and automated translation**, with a structured translation artifact,
   corrected transcript as the normal source, an explicit raw/dirty source option, and
   optional manual revision of automated output.
5. **v0.4 synchronized HTML transcript/export**, including the mock player, seeking,
   highlighting, accessibility, security, and raw/revised/translated-source tests in
   section 12.
6. **v0.4 optional project-scoped dictionaries**, conditional on benchmark evidence;
   later public-corpus work may also propose a separate optional general Polish resource,
   but neither kind is inherited or enabled silently.
7. After functional requirements and private-corpus validation, run separately licensed
   public-corpus WER and diarization benchmarks described in section 9.
8. Remaining audio, discovery, benchmark, subtitle, distribution, and operations work
   based on observed value and risk.
9. GUI after the planned core functions are stable; GUI reuses application services and
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

The retained private package includes canonical results and raw exports, editable review
files, immutable revision and audit artifacts, and revised TXT/SRT/VTT/segments exports.
Future benchmark tooling must treat the accepted revisions as gold without requiring the
corpus itself to live in this repository.

Within each compatible base-result lineage, the highest revision number is the accepted
gold transcript. Lower revisions remain immutable historical/intermediate states rather
than being discarded. Benchmark manifests must resolve this by exact base-result hash
and revision number, never modification time or filename order alone. They should expose
at least two correction tasks when an intermediate revision exists:

- raw canonical result -> latest accepted gold, measuring complete ASR correction;
- earlier revision -> latest accepted gold, measuring incremental cleanup of text that
  has already received human review.

Earlier revisions are useful benchmark inputs but are not alternate gold references.
Evaluation must also measure harmful changes to text that was already correct.

## 1. Manual transcript correction — promoted to v0.2.0

The following is no longer an unscheduled roadmap idea. It is the implemented v0.2.0 contract:

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

## 2. Automated transcript correction — in progress for v0.3

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
- require corrected editable text from the provider; the local revision engine derives
  exact source spans, before/after text, deterministic categories, and the authoritative
  audit. Optional provider change annotations remain advisory evidence;
- model/prompt/config provenance is persisted without secrets;
- LLM revisions may be direct siblings of manual gold for benchmark comparison;
- a model revision may later have a manual child revision, with parent provenance but a
  complete standalone child snapshot.

Benchmarking must cover local and cloud providers separately and report at least lexical
accuracy against manual gold, locally derived change precision/recall, unsupported or stylistic
changes, speaker-attribution preservation, audit completeness, latency, request/token
volume, estimated or actual cost, and failure/retry behavior. Provider-annotation precision
is reported separately only where annotations exist. A reviewer must be able to
prepare, manually correct, apply, audit, and export an LLM-produced revision through the
same workflow used for manual revisions.

Later benchmark automation should use supported backend APIs to load and, where available,
unload models,
wait for exact model readiness, run an explicit model x quantization x prompt x chunking
matrix, collect timing/resource/failure evidence, and unload cleanly without continuous
operator supervision. The observed LM Studio 0.4.21 server advertises native model
listing/loading and download-status endpoints in addition to its OpenAI-compatible
inference API; an unload mechanism must be verified against the selected backend/version
before automation relies on it. Other backends require separate adapters.
Every run identity and report must distinguish exact model identifier, quantization,
backend/version, prompt ID and content hash, output mode, chunk settings, context window,
sampling parameters, and hardware. Automation must retain bounded retries, private resume
state, sanitized logs, and the manual final-acceptance gate. It must never initiate paid
cloud runs or broaden API consent without separate explicit authorization.

Provider integration also requires deterministic mocked tests, secret-safe
configuration, timeout/rate-limit/retry handling, resumable failure-isolated batches,
and the consent/privacy contract in `11-security-and-privacy.md`.

The OpenRouter adapter and offline safety tests are implemented. A paid cloud pilot remains
an operator gate requiring an environment-only key, exact live model-slug confirmation,
explicit `--allow-cloud`, scoped consent, and separate authorization. Planned candidates
remain Qwen 2.5 72B Instruct and the exact currently available DeepSeek V3-family slug;
neither may be silently replaced when the catalog changes.
Gemini 2.5 Flash (`google/gemini-2.5-flash` when confirmed by the live catalog) is also a
cloud candidate. Its reasoning budget must be explicit and reported; the first comparable
baseline disables thinking, while enabled reasoning is a separate cost/quality experiment.

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

## 3. Optional dictionaries — project-scoped work planned for v0.4

Dictionary support remains conditional on benchmark evidence and is not part of v0.2.0.

Project dictionaries, if implemented:

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

Dictionary entries may be supplied manually or proposed by analyzing accepted revision
audits for frequent and consistent corrections, including proper names and canonical
forms such as `OpenAI` versus `Open AI`. Automatically discovered items are candidates
only: a user must approve them before they affect correction or translation. Benchmarks
must compare no-dictionary and selected-dictionary runs and detect harmful replacements.
Initial private-corpus candidates include phrase-aware normalization of recurring
`nabiało`/`nabiał` ASR forms to spoken `na biało`, plus the project email's spoken and
written forms (for example `małpaetyka` and `kontakt@etykawpetli.pl`). These examples must
remain project-scoped; they are not safe global replacements. Dictionaries should also
support explicitly approved equivalent aliases for correction and scoring, for example
the Latinized `Csikszentmihalyi` and diacritic `Csíkszentmihályi`. Equivalence must not be
implemented through global accent folding because Polish diacritics are lexically
meaningful.
The course name `AIDEAS` and its ASR/model variants such as `Ideas` or `IDEAS` are another
initial project-specific candidate: a merely plausible capitalization repair is not a
substitute for the approved canonical name.

The correction benchmark must test two dictionary hypotheses explicitly:

- whether the same LLM with an approved project dictionary is materially closer to manual
  gold than the identical model/prompt without one, especially for recurring proper names
  and project spelling conventions;
- whether manual review starting from an LLM candidate reduces reviewer time and accepted
  edit count relative to starting from raw ASR, both without and with dictionary context.

Use a four-branch matrix—raw ASR, LLM only, dictionary-assisted LLM, and manual gold—and
record lexical error, harmful/style changes, reviewer corrections, and review time. A
dictionary is accepted only if gains are not offset by confident harmful replacements.

After all functional requirements and the private benchmark are complete, BIGOS may also
be evaluated as a candidate source for an optional general Polish dictionary. Such a
resource must live in a separate repository catalog from project dictionaries, be
versioned and disabled by default, and require explicit selection. Dataset license and
redistribution terms must be reviewed before committing derived entries. Training or
dictionary-extraction partitions must be disjoint from held-out evaluation partitions;
the same examples cannot both teach the dictionary and inflate its reported WER result.
The no-dictionary baseline remains mandatory.

The next private correction benchmark is deliberately deferred rather than part of the
immediate v0.3 acceptance path. It must first publish later immutable manual-gold revisions
for the errata recorded in `22-v0.3-automated-correction.md`, rebuild the exact-hash
manifest, and rerun the established Gemini baseline. The current full-corpus run remains
the baseline for implementation decisions until that scheduled revalidation.

## 4. Manual translation pipeline — planned for v0.4

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

## 5. Automated translation — planned for v0.4

After manual translation establishes ground truth:

- add local/cloud API translation providers;
- retain provider/model/prompt/config provenance;
- use configurable chunks/context appropriate to the model;
- preserve sentence-level source mapping and source time spans;
- allow manual revision of automated translations;
- benchmark automated output against manual translations separately from transcript
  correction quality.

Both manual and automated translation must support a later manual revision pass, exact
source/parent lineage, batch resume and failure isolation, and deterministic regeneration
of every translated export. Evaluation must keep translation quality separate from
upstream ASR/correction quality.

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
- optional `cpu-only`;
- optional Apple Silicon preset after a compatible application build exists;
- automatic batch-size selection;
- bundled or explicitly downloaded licensed audio samples;
- benchmark of speed, VRAM, WER, timestamps, and diarization;
- repeatable wall-clock, real-time-factor, per-stage duration, peak process RAM, and
  sampled peak VRAM measurements for every preset comparison;
- retain raw measurement provenance so later hardware and dependency baselines can be
  compared without relying on terminal summaries;
- HTML/JSON report;
- hardware comparison.

These names are roadmap targets, not current compatibility or quality claims. Preset
acceptance requires complete transcription and correction benchmarks on its stated
hardware. No preset below the GTX 1070 target is planned.

### Low-VRAM local correction target

The lowest planned GPU tier will be physically validated on a PC with an NVIDIA GTX 1070
in addition to later testing on the reference RTX 3090. Candidate instruction models and
quantizations are:

- Bielik 3.0 11B Instruct: IQ4_XS or Q3_K_L;
- Qwen 2.5 7B Instruct: Q5_K_M or Q6_K;
- Llama 3.1 8B Instruct: Q5_K_M;
- Gemma 2 9B Instruct: Q4_K_M.

Final membership depends on measured load success, memory headroom, throughput, correction
quality, faithful-speech behavior, and complete-job stability. Merely loading a model does
not qualify it.

Initial reference-workstation evidence for the quality-first local tier: Qwen 2.5 14B
Instruct Q8_0 loaded in LM Studio with a 32K context and used approximately 18.5 GB VRAM
on the 24 GB RTX 3090. Bielik 3.0 11B Instruct will compare Q8_0 against F16 with CPU
offload. These observations are configuration-specific baselines, not guarantees for
other systems.

### Optional CPU-only correction target

The CPU-only preset targets a recommended minimum of 16 GB system RAM. Candidates are:

- Bielik 3.0 11B Instruct: Q5_K_M or Q6_K;
- Qwen 2.5 14B Instruct: Q4_K_M;
- Mistral NeMo 12B Instruct: Q4_K_M.

Benchmark reports must include CPU model, usable RAM, thread settings, latency, throughput,
peak process RAM, correction quality, and whether swapping occurred. The 16 GB figure is a
planned validation floor, not an accepted requirement until those runs pass. The planned
physical CPU-only validation machine has 32 GB RAM; operation below 16 GB is out of scope.

### Optional Apple Silicon correction target

Apple Silicon support is deferred until all functional requirements are complete and a
separate compatible transcriber build has been prepared. The planned minimum is 16 GB
unified memory. Candidates are:

- Bielik 3.0 11B Instruct: Q5_K_M, Q4_K_M, or MLX 4-bit;
- Qwen 2.5 14B Instruct: Q4_K_M or MLX 4-bit;
- Mistral NeMo 12B Instruct: Q4_K_M;
- Qwen 2.5 7B Instruct: Q8;
- Llama 3.1 8B Instruct: Q8.

Because no local Mac is available, validation may use explicitly rented Apple hardware
from MacinCloud and/or Scaleway. This is infrastructure access, not permission to send the
private corpus to an unrelated LLM API. Tests should cover the native CLI first and the GUI
when available, and record the exact Apple chip, unified memory, OS, runtime/backend,
quantization, cost, and benchmark provenance.

The expanded manual correction corpus should also become the reference source for lexical
correction benchmarks. Separate timestamp and diarization ground truth is still required
for timestamp/DER/JER evaluation.

### Public-dataset validation after functional completion

After all functional requirements pass and private-corpus evaluation is complete, add a
reproducible public-dataset matrix comparing supported ASR models, presets, correction
paths, and optional dictionaries. Candidate lexical/recording corpora are:

- BIGOS, for Polish WER evaluation and possible general-dictionary candidate extraction;
- Google FLEURS, for multilingual recordings and references;
- Mozilla Common Voice;
- Multilingual LibriSpeech.

Candidate diarization corpora are:

- VoxConverse;
- AMI Meeting Corpus.

Every dataset requires a pinned version/configuration, source and license record,
download/preparation hashes, official split preservation, normalization declaration,
language/subset selection, and a report of exclusions. WER/CER comparisons must not mix
dictionary-training material into their held-out test split. Diarization experiments must
report DER/JER methodology, collar and overlap policy, speaker-count assumptions, and the
exact pyannote/segmentation settings. Results should be presented as a table alongside
the private real-podcast benchmark, not merged into one opaque score.

An optional later real-world tier may add a small number of long-form public YouTube
podcast discussions with three or more speakers. Inclusion requires a separate license,
terms, privacy, and redistribution review plus manually verified references. URLs or
public availability alone do not authorize committing media or transcripts. This tier is
supplementary and does not replace controlled WER or diarization corpora.

## 10. Advanced channel handling — later, release unassigned

This remains on the later roadmap without an assigned release and is not on the current
critical path.

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

## 12. Platform transcript delivery and HTML — planned for v0.4

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

Acceptance includes a self-contained mock/placeholder site with a real HTML audio player
and time-linked transcript. Playback highlights or follows the active cue, and activating
a transcript sentence seeks the player to that sentence's start time. Tests must cover
keyboard operation, accessible semantics, escaping/untrusted transcript text, and use
with both raw and revised transcript sources.

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

- For v0.3, provide a reviewable fresh-install and verification script that installs and
  verifies prerequisites, the locked application environment, model readiness, and
  diagnostics while retaining explicit consent for gated model access and avoiding
  hidden system changes. Updating an existing installation is a separate workflow and
  must not be silently folded into the fresh-install script.
- For v0.3, restructure the root README with concise `Prerequisites`, `How to install`,
  and `How to use` sections. Prerequisites must summarize supported WSL2/bare-metal
  Ubuntu shapes, required Ubuntu packages, the validated software/hardware stack, a
  recommended minimum of 20 GB on preferably SSD storage, and the fact that RAM/VRAM
  requirements remain pending preset validation. Installation must briefly invoke the
  fresh-install script. Usage must show representative transcription and staged review
  command syntax and link to the complete `Instructions/` runbook.
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
