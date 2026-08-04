# ADR-0011: Language-specific offline alignment selection

- Status: accepted
- Date: 2026-08-04

## Decision

The MVP retains explicit `pl`, `en`, and `auto` language modes with multilingual
large-v2 as the shared ASR model. Word alignment is selected after ASR language
detection:

- Polish uses `jonatasgrosman/wav2vec2-large-xlsr-53-polish` at revision
  `6b1cea36bd8bc5f65ec8081667cd9c0207d51970`;
- English uses `facebook/wav2vec2-base-960h` at revision
  `22aad52d435eb6dbaf354bdad9b0da84ce7d6156`.

Both aligners are loaded from explicit Hugging Face snapshot directories with local-only
loading. Transcription must never fall back to an implicit TorchAudio or Hugging Face
download. In `auto` mode, no language is forced into large-v2; the detected `pl` or `en`
language selects the corresponding aligner for the whole recording.

## Evidence

Commit `aafd879` or later passed all 238 automated tests. Unit coverage proves that:

- explicit `pl`, `en`, and `auto` CLI overrides reach effective configuration;
- `auto` omits the backend language override and preserves detected language;
- the English snapshot is selected for an English transcription;
- an unsupported detected language fails instead of selecting the wrong aligner;
- `doctor` applies language-dependent model readiness.

On the reference Ubuntu 24.04 WSL2 workstation, the English snapshot was explicitly
downloaded without `HF_TOKEN`. The repository metadata resolved to 11 files at the exact
configured revision. The standard cache snapshot contained non-empty configuration and
vocabulary files.

`doctor` passed for `pl`, `en`, and `auto`. With Hugging Face Hub and Transformers set
offline, Transformers loaded the processor and `Wav2Vec2ForCTC` from the local snapshot,
reporting vocabulary size 32 and model type `wav2vec2`.

Transformers reported that `wav2vec2.masked_spec_embed` was newly initialized. This
parameter is associated with training-time masking and does not block evaluation-mode
inference. The warning is retained as evidence and does not authorize network access or
model mutation.

## Consequences and limits

English and automatic language selection are operationally available without confusing
the Polish and English aligners. English transcription and alignment quality remain
provisional because no English audio or manually verified English reference corpus has
yet been executed. The risk remains tracked as R-013 and must be revisited when an
English sample becomes available.

The MVP supports only Polish and English alignment. If automatic ASR detects another
language, the job fails clearly rather than silently using an incompatible model.
