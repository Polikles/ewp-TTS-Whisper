# Corpus lexical quality evaluation

## 1. Purpose

`tools/evaluate_corpus.py` compares generated hypotheses with independently, manually
verified UTF-8 transcripts. It produces:

- a machine-readable JSON report with per-case WER/CER and error counts;
- unweighted macro-average WER/CER, so a long case does not dominate;
- supplementary micro-average WER/CER and aggregate counts;
- an error-only normalized word diff for human review.

The evaluator never treats another model's uncorrected output as ground truth. It does
not score punctuation, capitalization, sentence layout, timestamps, or speaker labels.
Timestamp and diarization metrics require separate annotated references.
Their functional-MVP deferral and concrete reopening criteria are recorded in
[ADR-0014](adr/0014-dataset-dependent-quality-gates.md).

## 2. Strict evaluation manifest

The external corpus manifest uses TOML and safe relative paths:

```toml
manifest_version = "1.0"
normalization = "ewp-phase0-lexical-v1"

[[cases]]
case_id = "P0-01"
language = "pl"
reference_path = "references/p0-01-single-short.txt"
reference_sha256 = "a06bbc24b898ccbfba5845e544194d19cbe65219b4170be875ee9b6689e15dbc"
hypothesis_path = "p0-01-single-short_results.json"
hypothesis_format = "canonical-json"
```

Every case must contain exactly these six fields. Case IDs must be unique. Reference
hashes are mandatory, and evaluation stops if a manually verified reference has changed.
Absolute paths and parent traversal are rejected.

`reference_path` is relative to the manifest directory. `hypothesis_path` is relative to
the separately supplied hypothesis root, allowing immutable corpus references and
generated application results to remain in different external directories.

Supported hypothesis formats:

- `text` — plain UTF-8 hypothesis;
- `whisperx-json` — root `segments[].text`;
- `canonical-json` — `transcript.segments[].text` from EWP-transcripts results;
- `auto` — text by extension, otherwise structural JSON detection.

## 3. Run the evaluator

```bash
uv run --locked python tools/evaluate_corpus.py \
    /path/to/dataset/manifest.toml \
    --hypothesis-root /path/to/generated-results \
    --output /path/to/evidence/quality-report.json \
    --diff-output /path/to/evidence/quality-errors.diff.txt
```

Reports contain file-relative provenance and SHA-256 values, never transcript text. The
diff contains only normalized changed words, but it is still derived transcript content:
keep it with the external corpus evidence and do not commit it to the application
repository unless the corpus license and privacy policy explicitly permit that.

## 4. Normalization and interpretation

`ewp-phase0-lexical-v1` applies Unicode NFC and case folding, replaces Unicode
punctuation and whitespace with spaces, and collapses whitespace. It preserves Polish
diacritics, fillers, repetitions, symbols, lexical content, and written-versus-digit
number forms.

WER/CER uses deterministic Levenshtein counts. The review diff uses a memory-bounded
sequence comparison and is explanatory rather than another metric; its displayed edit
grouping need not equal the WER alignment decomposition.

Macro averages are the primary initial comparison because each selected case contributes
equally. Micro averages remain visible to show corpus-wide unit counts. The current
three-case material is only an initial baseline; release thresholds require the larger
licensed and manually verified archive-derived corpus.

## 5. Automated-correction benchmark manifests

v0.3 correction evaluation uses a separate strict manifest because every case binds four
roles: exact canonical base, selected source (`canonical` or earlier `revision`),
candidate revision, and latest accepted gold revision. Every path is safe and relative;
every artifact has an expected SHA-256. Revision compatibility is validated against the
exact canonical base before scoring.

This supports both accepted private-corpus tasks: canonical to latest gold and earlier
revision to later gold. Reports contain hashes, lineage revision numbers, baseline and
candidate WER/CER, word-error reduction, and excess word errors, but no transcript text.
The current report is the lexical foundation; locally derived change precision/recall,
unsupported or stylistic changes, speaker preservation, audit completeness, latency,
volume, cost, and retry outcomes remain required before provider acceptance.
Optional provider-annotation precision/recall is reported only for providers that expose
annotations; annotations never replace the local change list.

## 6. Later public benchmark matrix

After functional requirements and private-corpus evaluation, qualify public datasets in
separate, versioned manifests. Initial candidates are BIGOS, Google FLEURS, Mozilla
Common Voice, and Multilingual LibriSpeech for lexical/multilingual evaluation, plus
VoxConverse and AMI Meeting Corpus for diarization settings. Dataset licenses, official
splits, preparation hashes, normalization, exclusions, and metric policies must be
recorded per corpus rather than assumed interchangeable.

Any general Polish dictionary derived from BIGOS must use a training partition disjoint
from the held-out WER partition and remain an optional, separately versioned artifact.
Reports retain a no-dictionary baseline and compare datasets in a table without collapsing
them into one score. A later supplementary three-or-more-speaker YouTube podcast tier
requires independently verified references and explicit permission/licensing review.
