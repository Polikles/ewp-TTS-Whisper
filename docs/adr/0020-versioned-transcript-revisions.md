# ADR-0020: Versioned full-snapshot transcript revisions

- Status: accepted
- Date: 2026-08-14

## Decision

The application will add a versioned transcript-revision layer after the immutable
canonical ASR result.

`results.json` remains unchanged and continues to record the output of transcription,
word alignment, and speaker attribution. Editorial correction does not mutate that file.

A correction produces a separate schema-valid revision artifact. Every revision is a
complete snapshot of the corrected transcript and maps corrected text back to stable
canonical `word_id` anchors. A revision may reference a parent revision for provenance,
but rendering the revision never requires replaying parent deltas.

Normal correction changes text and speaker attribution only. Canonical timestamps remain
immutable. A runtime `EffectiveTranscript` resolves corrected tokens against canonical
word timing and becomes the common input for TXT, SRT, VTT, segments JSON, and future HTML
exporters.

Manual review uses a versioned human-readable `EWP-REVIEW 1` text format. Machine-owned
anchors divide the canonical word timeline into bounded alignment windows, while ordinary
text and speaker directives remain easy to edit in an external text editor. Applying a
review uses deterministic anchored token alignment and creates a new full revision.

The same revision engine and alignment path will later accept LLM correction and GUI
edits. Those interfaces must not introduce a second corrected transcript model.

## Context

The v0.1 canonical model intentionally contains both segment text and word text because it
represents normalized ASR output. Existing TXT export primarily consumes segment text,
while subtitle generation is word/timing oriented. Directly editing canonical text would
therefore create multiple mutable text representations and would weaken the ability to
reproduce the original ASR output.

Manual correction is also required to create a ground-truth corpus before automated
correction is evaluated. Reviewers need a readable text workflow rather than editing a
large canonical JSON document.

Some corrections change token topology:

- one ASR word can become multiple corrected words;
- multiple ASR words can become one corrected word or proper name;
- a word can be inserted or deleted;
- punctuation can change sentence boundaries without changing timing materially;
- a short interjection can be reassigned to another existing speaker.

These cases require stable mapping to the source timeline but do not normally justify
rerunning ASR or manually authoring timestamps.

## Consequences

### Positive

- canonical ASR evidence remains reproducible and recoverable after bad corrections;
- every corrected export is derived from one structured revision rather than maintained
  independently;
- full snapshots are simple to read, validate, move, benchmark, and export;
- parent metadata supports manual-after-LLM history without making children dependent on
  parent replay;
- sibling revisions can represent manual gold and competing model outputs from the same
  base result;
- ordinary correction remains independent of source audio and GPU/ML dependencies;
- one `EffectiveTranscript` boundary removes exporter dependence on competing canonical
  text fields;
- external-editor CLI, future LLM correction, and future GUI share application logic;
- the model remains compatible with a later sentence-level translation pipeline.

### Negative

- full snapshots duplicate corrected transcript text between revisions;
- alignment logic must handle merge/split/insert/delete cases robustly;
- review anchors are visible in plain-text editing until a GUI hides them;
- insertion timing is necessarily approximate when no canonical source word exists;
- revision-aware export and output naming add another version identity to manage.

The storage cost is accepted because transcript JSON is small relative to source audio,
and independent full snapshots substantially simplify recovery and reproducibility.

## Rejected alternatives

### Edit `results.json` directly

Rejected because it destroys the original ASR result, makes correction mistakes harder to
recover from, and conflates recognition evidence with accepted editorial text.

### Hand-edit TXT/SRT/VTT independently

Rejected because formats drift and the same correction must be repeated. Derived exports
remain disposable and regeneratable.

### Store revisions only as patch/delta operations

Rejected as the primary representation because reading the latest state would require
replaying history and surviving missing/corrupt parent artifacts. Detailed diffs remain
optional audit data rather than reconstruction state.

### Require manual timestamps for corrected words

Rejected for normal revision because the dominant corrections are spelling, proper names,
grammatical endings, punctuation, sentence boundaries, and speaker attribution. Timing is
inherited from canonical word mappings. An explicit emergency timing-override mechanism
may be designed later if corpus evidence demonstrates a need.

### Persist manually maintained sentence IDs during correction

Rejected because punctuation-based sentenceization already serves TXT export and separate
sentence markers would substantially increase reviewer work. Sentence-level IDs can be
derived later when a translation pipeline needs them.

## Compatibility

- `schemas/results.schema.json` is not changed by this decision.
- raw `transcriber export` remains backward compatible and equivalent to selecting no
  revision.
- revision artifacts have their own schema/version.
- future translation may select either raw canonical text or one corrected revision as its
  source; translation remains a separate pipeline with a separate artifact schema.

## Follow-up

Normative details are specified in
[`../13-transcript-revisions.md`](../13-transcript-revisions.md). The v0.2.0 implementation
plan is in [`../21-v0.2.0-transcript-revision-plan.md`](../21-v0.2.0-transcript-revision-plan.md).
