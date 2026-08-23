# EWP-transcripts work status

Last updated: **2026-08-23**.

## Checkpoint

Version `0.3.0` is an internal beta on `main`; it is not tagged or published as a public
release. The repository is public and licensed under `AGPL-3.0-or-later`.

The v0.1 transcription/export baseline, v0.2 immutable manual transcript revisions, and
v0.3 local/cloud automated correction are implemented and acceptance-audited. Automated
correction remains a non-final review candidate. The accepted v0.3 evidence, provider
problems, prompt history, local/cloud pilots, complete Gemini corpus run, costs, and
limitations are recorded in `docs/22-v0.3-automated-correction.md`.

The first v0.4 vertical slice—manual Polish/English translation—is implemented:

- exact canonical or compatible transcript-revision source lineage;
- deterministic speaker-safe timed translation units;
- immutable `EWP-TRANSLATION 1` review and translation artifacts;
- single-file and failure-isolated batch prepare, preview, apply, audit, and export;
- deterministic UTF-8 TXT, SRT, and VTT output without audio or models;
- English closing-quote and known abbreviation/domain boundary handling, including
  legal case names such as `Battle v. Microsoft`;
- a complete operator playbook in `WSL config/TRANSLATE_TRANSCRIPTS.md`.

The first automated-translation and benchmark slices are also implemented in the current
working tree: provider-neutral single-owner unit requests, bounded read-only context, a
deterministic mock provider, retry/resume execution, immutable non-final candidates,
content-free operations reporting, exact-scope consent, and the first network-isolated LM
Studio adapter are present. Failure-isolated directory execution and explicit manual
acceptance as a new exact-parent manual translation are also implemented. In addition,
exact-hash automated candidates and compatible
manual references can be staged into
private per-unit assessments, and completed reviews produce content-free,
direction-specific semantic reports. Meaning fidelity is explicitly independent of
lexical overlap; names, project conventions, and selected-dictionary adherence are a
separate dimension. The first corrected LM Studio baseline is complete; manual acceptance
and the first exact-lineage semantic report remain pending.

The first real Bielik 11B v3 Q8 `s0e00` pilot completed operationally: 80 requests, zero
retries, 49,605 ms provider time, and complete resume reuse on publication. Its candidate
was rejected after review found JSON wrappers in 75/80 units, adjacent-context repetition,
an owned-unit omission, and a false numeric sentence split. Fixes are implemented for a
fresh zero-context rerun; no translation-quality claim is accepted from the failed pilot.
The rerun then showed Bielik's chat template adding a valid string `translator_notes`
and later `translation_notes` field. The adapter now discards only those two observed
aliases with an explicit per-unit warning; unknown provider metadata continues to fail
closed. Parser-version changes invalidate resume identity.
The resulting zero-context run completed 79 requests with zero retries in 28,854 ms and
fixed the numeric split, but manual review found 25 spurious outer-quote wrappers and three
`Szymon` to `Simon` anglicizations. Valid JSON-string responses are now unwrapped and the
prompt requires exact personal-name copying.
The fresh confirmation run completed 79 requests with zero retries in 26,833 ms, produced
1,051 target tokens, and emitted no provider warnings or spurious outer-quote wrappers.
Manual review found no omission, repetition, or ownership failure, but identified two clear
semantic errors and several minor wording/meaning issues. Bielik still anglicized `Szymon`
in three of four occurrences despite the prompt. The owner confirmed `Ethics in the Loop`
as the English title, `etykawpetli.pl` as the preferred Polish-domain spelling (both owned
spellings are valid), and initiator/catalyst as the intended sense of `aktywator`. The
candidate remains non-final; exact-parent manual correction is the next gate.
The first manual apply exposed that a separate accepted-output directory restarted child
numbering at one. Publication now allocates strictly after the recorded parent number;
the incorrectly numbered temporary artifact is rejected as qualification evidence.

External structural evidence is complete for this slice: the owner mapped the private
English corpus into the current scheme, applied and exported all files without errors,
and reported readable SRT/VTT output. This corpus permits artistic translation freedom,
so it validates workflow structure, not translation accuracy.

The quality gate at checkpoint commit `0ee7841` passed formatting, lint, type checks, and
all **544 tests**. Canonical results and accepted revisions remain immutable. Private
corpus content, API keys, provider payloads, and runtime resume/lock files remain outside
Git.

The current automated-translation and semantic-benchmark tree passes the same complete
gate with **573 tests**.

## Next session: ordered v0.4 work

Start with item 1 and complete one vertical slice at a time. These are the complete
remaining v0.4 workstreams; details and acceptance criteria live in
`docs/23-v0.4-translation-contract.md` and `docs/99-roadmap-v2.md`.

1. **Automated translation.** The provider-neutral request/response, mock, LM Studio,
   exact-scope consent, retry/resume, immutable candidate, and single-file CLI slice is
   implemented. Next run a real verified-Polish `pl -> en`, `preserve/preserve`,
   no-dictionary LM Studio pilot and inspect its operational evidence. This baseline is
   complete for Bielik. Next correct and accept its exact-parent review, then audit/export
   it. Keep `en -> pl` separate. Cloud translation remains a later adapter after the local
   pilot establishes the request/prompt baseline.
2. **Translation pipeline benchmark.** The exact-lineage human semantic assessment and
   content-free reporting boundary is implemented. Next define and approve the narrower
   reference, then validate preparation, provider execution, manual correction, apply,
   audit, and export. Compare local candidates Qwen 2.5 32B Q4,
   Bielik 11B Q8, Llama 3.3 8B Q8, MADLAD-400, and NLLB-200 separately from cloud models.
   Record model artifact, backend, prompt, chunking, latency, resource use, request/token
   volume, cost, retries, and reviewer effort. Do not claim translation accuracy from the
   artistically free English corpus; first define a narrower manually approved reference.
3. **Project-scoped dictionaries.** Implement explicit, hashed, optional dictionaries
   usable as correction/translation context. Candidate extraction from accepted audits
   requires human approval. Benchmark raw, LLM-only, dictionary-assisted LLM, and manual
   gold; reject dictionaries that create harmful confident replacements.
4. **Timed-event semantics.** Design and version the additive canonical JSON change for
   `speech`, `music`, `laugh`, `cough`, `note`, and compatibility defaults before either
   renderer infers non-speech presentation from text.
5. **YouTube TTML export.** Implement the small UTF-8 TTML 1.0-compatible YouTube profile
   in the roadmap, mapping each existing cue to one `<p>`, applying deterministic
   speaker styles/colors, and validating XML. Finish with an unlisted YouTube upload
   check for language, timing, labels, diacritics, and colors.
6. **Embeddable HTML transcript.** Emit the specified accessible, escaped, deterministic
   HTML fragment with no CSS, JavaScript, inline styles, or event handlers. Build the
   separate mock player site that supplies its own CSS/JavaScript and tests highlighting,
   seeking, keyboard use, light/dark presentation, and usable no-script fallback.
7. **v0.4 closure.** Reconcile requirements, traceability, operator documentation,
   changelog, schemas/examples, package version and artifacts. Run the full automated and
   packaging gates. Full clean-machine installation-through-workflow qualification stays
   deferred until most/all functional requirements exist; its first run is manual and
   later becomes automated.

## Explicitly deferred, not lost

- Sentence units remain the v1 translation timing/audit boundary. A separately versioned
  bounded speaker-chunk mode is added only if further corpus evidence shows repeated
  cross-sentence translation problems; existing artifacts never change interpretation.
- Correct and expand private benchmark references when a narrow translation-quality
  benchmark is designed. The grammar-edited Polish corpus is not ASR ground truth.
- Public-corpus WER/translation/diarization qualification, preset/hardware matrices,
  Apple Silicon support, CPU-only and GTX 1070 tiers, and automated model load/unload
  benchmarking remain later roadmap work.
- Content-aware arbitrary-extension discovery, audio repair/comparison, advanced 3+
  channel and surround handling, GUI, and additional subtitle/platform formats remain
  in `docs/99-roadmap-v2.md`; they are not v0.4 checkpoint blockers unless explicitly
  promoted.

## Operator and design entry points

- Complete CLI use: `Instructions/README.md`
- Manual transcript revisions: `WSL config/REVISE_TRANSCRIPTS.md`
- Manual translations and legacy migration: `WSL config/TRANSLATE_TRANSCRIPTS.md`
- v0.3 correction evidence: `docs/22-v0.3-automated-correction.md`
- v0.4 translation contract: `docs/23-v0.4-translation-contract.md`
- Complete prioritized/deferred roadmap: `docs/99-roadmap-v2.md`

Do not hand-edit canonical JSON. Preserve each original result and publish accepted text
only through immutable revision or translation artifacts.
