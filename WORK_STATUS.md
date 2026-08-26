# EWP-transcripts work status

Last updated: **2026-08-26**.

## Checkpoint

Version `0.7.0` is the next internal beta on `main`; it is not tagged or published as a public
release. The repository is public and licensed under `AGPL-3.0-only`.

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

The automated-translation and benchmark slices are also implemented on `main`:
provider-neutral single-owner unit requests, bounded read-only context, a
deterministic mock provider, retry/resume execution, immutable non-final candidates,
content-free operations reporting, exact-scope consent, and the first network-isolated LM
Studio adapter are present. Failure-isolated directory execution and explicit manual
acceptance as a new exact-parent manual translation are also implemented. In addition,
exact-hash automated candidates and compatible
manual references can be staged into
private per-unit assessments, and completed reviews produce content-free,
direction-specific semantic reports. Meaning fidelity is explicitly independent of
lexical overlap; names, project conventions, and selected-dictionary adherence are a
separate dimension. The corrected LM Studio baseline, manual acceptance, exact-lineage
semantic report, and project-dictionary comparison are complete.

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
candidate remained non-final until the exact-parent manual correction described below.
The first manual apply exposed that a separate accepted-output directory restarted child
numbering at one. Publication now allocates strictly after the recorded parent number;
the incorrectly numbered temporary artifact is rejected as qualification evidence.
After that fix, the corrected review published as exact-parent manual child translation 2,
its 79-unit audit published successfully, and deterministic TXT, SRT, and VTT exports were
written successfully. The automated candidate-to-manual-acceptance workflow is therefore
qualified end to end for this pilot. Its exact-lineage semantic assessment and content-free
benchmark report, described next, completed the gate.
That report is now complete for `pl -> en`: 79 units, 71 faithful, 6 minor errors,
2 major errors, no critical errors, semantic pass rate `0.89873418`, and 6 separately
counted convention failures. Issue totals are 1 addition, 5 mistranslations, and 2
tone/register errors; dictionary provenance is null. The Bielik no-dictionary baseline is
therefore complete and must not be merged with later dictionary-assisted or reverse-direction
runs.

External structural evidence is complete for this slice: the owner mapped the private
English corpus into the current scheme, applied and exported all files without errors,
and reported readable SRT/VTT output. This corpus permits artistic translation freedom,
so it validates workflow structure, not translation accuracy.

The current v0.6 tree passes formatting, lint, type checks, and all **617 tests**. A fresh
Ubuntu 24.04.4 WSL2 installation on an RTX 3090 passed environment installation, pinned-model
setup, offline transcription, restart-safe canonical replay, Gemini 2.5 Flash correction,
candidate-backed manual-review preparation, verified-revision export, and LM Studio/Bielik
translation candidate, audit, and review preparation. Canonical results and accepted
revisions remain immutable. Private corpus content, API keys,
provider payloads, and runtime resume/lock files remain outside Git.

The cross-cutting diagnostic catalogue is implemented. Expected application exceptions,
direct privacy/non-final warnings, benchmark and dictionary command failures, explicit CLI
validation, and framework-generated usage errors now print stable codes. Batch failures reuse
the same application codes. `docs/25-warning-error-catalog.md` documents meaning, likely
cause, safety implications, and operator action, and tests reject undocumented emitted codes.

The `0.7.0` package candidate passes the 620-test locked gate and the 140-package environment
compatibility check. Its wheel and source archive contain the expected license metadata/files
and no runtime/private payload filenames or credential-shaped values. An external `/tmp`
target installation proved wheel provenance outside the checkout, version/help, coded usage
errors, and all six model-free export formats. Exact candidate hashes are recorded in the
ADR-0010 follow-up; this targeted artifact smoke complements rather than repeats the earlier
full isolated locked-dependency installation.

## v0.4 delivered work

These are the delivered v0.4 workstreams; details and acceptance criteria live in
`docs/23-v0.4-translation-contract.md` and `docs/99-roadmap-v2.md`.

1. **Automated translation.** The provider-neutral request/response, mock, LM Studio,
   exact-scope consent, retry/resume, immutable candidate, and single-file CLI slice is
   implemented. The verified-Polish `pl -> en`, `preserve/preserve`, no-dictionary Bielik
   baseline is complete, including exact-parent manual acceptance, audit, export, and the
   semantic assessment/report. Keep `en -> pl` separate.
   Local LLM translation is operationally usable, but it is not recommended for
   publication-quality output on current evidence: Bielik remains noticeably mechanical
   and requires comprehensive human semantic/convention review. This gate primarily
   qualified LM Studio compatibility, failure handling, provenance, resume, review, and
   export—not a broad model-quality ranking. Additional local models and settings were
   intentionally not exhaustively tested.
2. **Translation pipeline benchmark.** The exact-lineage human semantic assessment and
   content-free reporting boundary is implemented. The first narrower Bielik reference and
   complete candidate/correction/apply/audit/export/report path are qualified. Optional
   post-functional quality work may compare local candidates Qwen 2.5 32B Q4, Bielik 11B Q8,
   Llama 3.3 8B Q8, MADLAD-400, and NLLB-200 separately from cloud models once semantic
   assessment can scale without whole-corpus manual review.
   Record model artifact, backend, prompt, chunking, latency, resource use, request/token
   volume, cost, retries, and reviewer effort. Do not claim translation accuracy from the
   artistically free English corpus; first define a narrower manually approved reference.
3. **Project-scoped dictionaries.** The first strict, explicit, hashed translation-context
   slice is implemented. Extend the same contract to Polish automated correction, using
   Gemini 2.5 Flash because evaluated local models did not improve ASR error rate, and add
   operator examples
   and dictionary-assisted benchmark evidence. Candidate extraction from accepted audits
   requires human approval. Benchmark raw, LLM-only, dictionary-assisted LLM, and manual
   gold; reject dictionaries that create harmful confident replacements.
   The first exploratory translation-dictionary run demonstrated such harm: the complete
   dictionary was sent to every unit and Bielik invented an unrelated speaker label. Request
   planning now exposes only entries whose source form occurs in the owned unit. That run is
   rejected; the next pilot must use only durable names/titles/addresses, not episode-specific
   mistranslation fixes. The subsequent scoped pilot is described below.
   Dictionary provenance is first-class and inherited by exact-parent manual children;
   audits declare the dictionary object or null, while exports publish a provenance sidecar.
   The accepted general project-dictionary pilot preserved semantic performance at 71/79
   faithful (`0.89873418`) while reducing convention failures from 6 to 2. It produced the
   same 6 minor and 2 major semantic errors as the no-dictionary baseline. Per-unit source
   filtering caused no harmful insertion, but Bielik still anglicized 2/4 `Szymon`
   occurrences, so dictionaries are context assistance rather than enforcement.
   The intended stage order is `transcript -> Gemini-assisted Polish review candidate ->
   manual Polish review -> export -> translation (manual or LLM-assisted)`. Translation
   normally starts from the accepted Polish revision. Explicit translation from an
   unreviewed candidate remains supported with a prominent warning and exact
   `automated_candidate` source lineage. Correction and
   translation dictionaries remain separately versioned and hashed even when they share
   approved identifiers.
   Polish correction-dictionary proposal and approval are now implemented: exact compatible
   manual revisions yield pending repeated/consistent mappings, every item must be manually
   approved or rejected, and the published project dictionary retains proposal and corpus
   lineage. The initial context-free private proposal was rejected after ambiguous short
   forms and punctuation-bearing keys were observed. Proposal v1.1 adds marked source/target
   context per occurrence and strips only boundary punctuation from lexical keys. A fresh
   `/tmp` pilot found 41 pending candidates across 22 compatible cases with context on every
   item and no punctuation-bearing boundary keys. Explicit Gemini/OpenRouter selection,
   per-chunk source matching, resume identity, revision provenance, and audit reporting are
   implemented. The subsequent manual proposal review and controlled dictionary comparisons
   are recorded below.
   The owner reviewed proposal v1.1: 19 mappings were approved and 22 rejected. Both decision
   classes are retained so rejected mappings remain suppressed in later proposals; only
   approved entries are provider context. The redistributable proposal and dictionary are
   published in the versioned `dictionaries/` catalog with exact SHA-256 values
   `7556eb83...43152` and `5d1bb1c5...15db`; automated tests verify their lineage and counts.
   A dictionary-assisted Gemini 2.5 Flash `s0e01` smoke then completed four requests with no
   retries in 25,442 ms for `$0.023449`, preserving all 2,411 tokens and speaker attribution
   while proposing 17 substitutions with no warnings. This proves operation and provenance,
   not quality; an identical no-dictionary control and exact manual-gold comparison are next.
   That comparison is complete but in-sample: no-dictionary Gemini removed 2/72 errors
   (`0.02926421` WER), while dictionary-assisted Gemini removed 10/72 (`0.02591973` WER),
   with exact-edit precision/recall improving from `0.66666667`/`0.05882353` to
   `0.76470588`/`0.38235294`. Because `s0e01` contributed to dictionary derivation, this proves
   adherence rather than generalization; four unsupported exact edits also need manual review.
   Runtime scope is being corrected so derivation job IDs remain audit evidence while explicit
   matching project selection permits a genuinely held-out/future-episode comparison.
   The held-out `s0e00` comparison now supplies generalization evidence: dictionary-assisted
   Gemini halved raw WER from `0.02561118` (22 errors) to `0.01280559` (11), versus
   `0.02211874` (19) without a dictionary. Exact-edit precision/recall/F1 were
   `0.82352941`/`0.7`/`0.75675676`, versus `1.0`/`0.15`/`0.26086957` for the conservative
   control. Runtime/cost were nearly equal and both preserved tokens/speakers without warnings.
   Manual classification of three dictionary-assisted edits unsupported by gold is the final
   acceptance gate before expanding the dictionary-assisted correction benchmark.
   The owner classified all three as supported convention edits: ASCII `etykawpetli.pl` is the
   preferred spelling of the owned address, while the diacritic spelling is also valid. No
   harmful held-out edit was identified. The dictionary-assisted held-out pilot is therefore
   accepted, with 14 exact-gold plus 3 owner-supported convention edits. Review output now
   explains that lexical normalization may visually separate domain punctuation without
   changing the candidate artifact.
4. **Timed-event semantics.** The additive schema `1.1` foundation is implemented with segment
   kinds `speech`, `music`, `laugh`, `cough`, and `note`; legacy omissions default to speech.
   Raw/revised effective projection, derived segment JSON, and subtitle cue planning preserve
   kind without changing SRT/VTT presentation. Explicit non-speech authoring remains separate;
   YTT and HTML may now consume the shared semantic field without inferring it from text.
5. **YouTube srv3 YTT export.** Two standards-based TTML uploads were accepted and verified
   timing, turn labels, language, and Polish diacritics, but YouTube discarded wrapping,
   centering, and colors even when encoded inline. The failed profile has been replaced by
   deterministic YouTube srv3 timed-text XML based on the owner-supplied accepted example.
   It reuses planned cues/line breaks, numeric speaker pens, centered bottom placement, and
   a separate non-speech pen. The first srv3 upload correctly centered cues and preserved
   text/timing, but YouTube flattened `<br/>` line elements. The owner-supplied corrected
   template uses literal in-paragraph newlines and near-white `#FEFEFE`; the renderer now
   matches that structure byte-for-byte. The final unlisted upload fully passed: two-line
   wrapping, distinct speaker colors, centering, timing, turn labels, and Polish diacritics
   all rendered correctly. YTT remains opt-in because it is platform-specific, not because
   qualification is pending.
6. **Embeddable HTML transcript.** Raw and manually revised `--format html` export is
   implemented as an escaped deterministic fragment with a BCP 47 language, explicit
   speaker turns, sentence-level native buttons, integer timing/speaker/kind metadata, and
   no CSS, JavaScript, inline styles, or event handlers. Immutable translation artifacts
   now export the same HTML contract using target language/text and inherited unit timing.
   The separate mock player site is implemented with its own CSS/JavaScript and contract
   tests for highlighting, seeking, native keyboard activation, reduced-motion-aware
   following, light/dark presentation, and readable no-script structure. A manual browser
   pilot passed Firefox/LibreWolf audio, mouse/keyboard seeking, highlighting, following,
   and light/dark rendering, but Chromium-family clicks restarted at zero. The retry waits
   for metadata and seek completion; explicit theme and auto-follow controls were added.
   A second Chromium retry isolated the remaining failure to Python's basic static server;
   the example now includes a range-capable server and byte-range calculation tests. The
   final retry returned valid `206 Partial Content` and passed seeking in Chrome and Brave;
   Firefox and LibreWolf had already passed. Theme/auto-follow controls and the no-script
   fallback also passed. The HTML slice is accepted. Minor acoustic spill across an
   occasional sentence boundary is inherited from word alignment and explicitly deferred;
   the renderer must not apply heuristic timestamp shifts.
7. **v0.4 closure.** Requirements, traceability, operator documentation, changelog,
   schemas/examples, and package version are reconciled. The full locked gate passes with
   603 tests, and the 0.4.0 wheel/source archives pass metadata, privacy-content, and isolated
   installed-wheel CLI/HTML/YTT smoke checks. The later beta-line clean-machine
   installation-through-workflow qualification also passed manually; repeatable automation
   may be added after the evidence format stabilizes.

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
