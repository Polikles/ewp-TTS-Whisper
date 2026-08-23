# Translate verified transcripts

This playbook covers the current manual-first Polish-to-English workflow. It mirrors
transcript revision:

```text
prepare -> edit in VS Code -> preview -> apply -> audit -> export
```

Translation never changes canonical `*_results.json` or transcript
`*_revision_NNN.json`. It creates a separate immutable translation snapshot.

## 1. Choose the source

Use the latest manually verified Polish revision. The current private Polish corpus also
contains deliberate grammar and readability corrections, so it is suitable as translation
source and LLM-correction reference. It is no longer a word-for-word ASR ground truth and
must not be used to claim speech recognition accuracy.

Example directories:

```bash
export EWP_PL_RESULTS="/absolute/path/to/private benchmark/PL/1 canonical outputs"
export EWP_PL_REVISIONS="/absolute/path/to/private benchmark/PL/3 apply"
export EWP_EN_REVIEWS="/absolute/path/to/private benchmark/EN/translation reviews"
export EWP_EN_TRANSLATIONS="/absolute/path/to/private benchmark/EN/applied"
export EWP_EN_EXPORTS="/absolute/path/to/private benchmark/EN/exports"
export EWP_EN_AUDITS="/absolute/path/to/private benchmark/EN/audits"
```

Use WSL paths or properly quoted Windows paths. Keep private corpus material outside Git.

## 2. Prepare translation reviews

Prepare the whole Polish corpus from the latest exact compatible revision for each result:

```bash
uv run --locked transcriber translate prepare "$EWP_PL_RESULTS" \
  --revision "$EWP_PL_REVISIONS" \
  --target-language en \
  --register preserve \
  --discourse preserve \
  --output-dir "$EWP_EN_REVIEWS"
```

`preserve/preserve` is correct for a casual podcast because it asks the translator to
retain the existing register instead of making it artificially more informal. A prepared
file is named `*_en.translation.review.txt` and contains:

```text
EWP-TRANSLATION 1
# metadata: {...}

@@ immutable unit metadata
< immutable Polish source text
> editable English target text
```

Only text after `> ` is editable. Do not change metadata, directives, source lines,
speaker IDs, timestamps, hashes, or token IDs.

## 3. Edit in VS Code

VS Code is the preferred editor. Enable word wrap and use search plus **Change All
Occurrences** for repeated terminology. Scope replacements carefully so Polish `< ` source
lines and machine-owned metadata remain unchanged.

Every `> ` line must contain the English translation of its corresponding `< ` line.
English may use different word order and punctuation, but it must retain facts, intent,
uncertainty, speaker identity, and casual podcast style. Remove model-added annotations
such as `[cite: 1]`; citations that were not spoken are not transcript content.

Sentence boundaries provide narrower subtitle timing and audit scope; they do not require
literal one-to-one syntax. Report false source splits rather than merging or deleting
machine-owned units. Known abbreviations such as `v.` in `Battle v. Microsoft` are treated
as non-ending tokens. A future version may add bounded speaker-chunk unitization if real
translation work shows that sentence units are consistently too restrictive.

If a web LLM is used, transcript text leaves the machine and the run is not reproducible
through the current CLI provider contract. Check the provider's privacy settings, never
send secrets, and manually review every target line. A useful instruction is:

```text
Translate Polish target content into natural English while preserving the casual podcast
style and meaning. Do not edit metadata, @@ directives, or < source lines. Fill only >
target lines. Do not add citations, notes, facts, summaries, or stylistic corrections.
```

Web-model output is editing assistance, not an accepted translation until preview, apply,
audit, and manual review succeed.

## 4. Migrate the existing English legacy reviews

Files currently under `EN/translations of the review files/*.review.txt` are translated
copies of `EWP-REVIEW 1`. Their `language` and other copied headers do not turn them into
translation artifacts. Do not run `revise apply` on them and do not hand-edit their hashes.

For each episode:

1. Prepare a fresh `*_en.translation.review.txt` from the corrected Polish revision.
2. Open the fresh translation review and the legacy English review side by side in VS Code.
3. Transfer English prose only into matching `> ` target lines.
4. When legacy speaker blocks and new sentence units differ, distribute the English by
   meaning so each `> ` line translates its adjacent `< ` source line.
5. Remove `[cite: N]`, Markdown fences, headings, and any other unspoken model additions.
6. Keep the legacy file unchanged as migration evidence until the new artifact is applied
   and audited.

There is intentionally no automatic legacy importer: artistic sentence restructuring
makes unsupervised redistribution across exact timed units unsafe.

## 5. Preview and apply

Validate all completed reviews without publication:

```bash
uv run --locked transcriber translate preview "$EWP_EN_REVIEWS" \
  --results "$EWP_PL_RESULTS" \
  --revisions-dir "$EWP_PL_REVISIONS"
```

Then publish immutable translations:

```bash
uv run --locked transcriber translate apply "$EWP_EN_REVIEWS" \
  --results "$EWP_PL_RESULTS" \
  --revisions-dir "$EWP_PL_REVISIONS" \
  --output-dir "$EWP_EN_TRANSLATIONS"
```

A batch failure returns exit code 5 without invalidating successful items. Fix and retry
only failed files; rerunning successful reviews creates later translation numbers.

## 6. Audit and export

Audit is currently single-file. It reconstructs exact Polish source text and pairs it with
English target text:

```bash
uv run --locked transcriber translate audit \
  "$EWP_EN_TRANSLATIONS/EPISODE_en_translation_001.json" \
  --results-dir "$EWP_PL_RESULTS" \
  --revisions-dir "$EWP_PL_REVISIONS" \
  --output-dir "$EWP_EN_AUDITS"
```

Export the full directory:

```bash
uv run --locked transcriber translate export "$EWP_EN_TRANSLATIONS" \
  --format txt --format srt --format vtt \
  --output-dir "$EWP_EN_EXPORTS"
```

English TXT preserves target units and does not re-split them around quotation marks.
SRT/VTT wrap by subtitle capacity; punctuation does not drive cue splitting. Target words
do not have alignment timestamps, so any necessary multi-cue split is distributed only
within the source unit's inherited interval.

## 7. Current acceptance goal

This corpus is not yet a translation-accuracy benchmark because approved English text
allows substantial artistic freedom. For now validate the pipeline:

- all expected reviews prepare from exact latest Polish revisions;
- only target text can change and every target unit is non-empty;
- preview and apply complete with no unexplained failures;
- audits reconstruct every Polish/English unit pair;
- TXT, SRT, and VTT export for all applied translations;
- English quotation punctuation such as `."` survives TXT and subtitles;
- SRT/VTT remain valid, chronological, bounded, and manually readable;
- no `[cite: N]` or other unspoken annotations remain;
- repeated application/export behaves according to immutable numbering and safe skip rules.

Record structural failures and manual corrections separately. Translation-quality metrics
can be designed later around narrower reference criteria; do not report BLEU, COMET, WER,
or a single accuracy score for the current artistically edited English corpus.
