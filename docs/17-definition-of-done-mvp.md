# Definition of Done — MVP

The MVP is complete when the following conditions are met.

## Functionality

- [ ] All FR requirements are implemented or explicitly deferred through an ADR.
- [x] `doctor`, `inspect`, `dry-run`, `transcribe`, `export`, and `clean` work.
- [x] A results JSON is always generated after successful transcription.
- [x] TXT, SRT, VTT, and optional segments JSON are generated without running ASR again.
- [x] Single file, directory batch, grouped files, dual mono, and split speakers work.
- [x] Diarization works for mixed mono/stereo.
- [x] SHA-256/signature-based skipping and versioning work.

## Quality

- [x] All examples pass JSON Schema validation.
- [ ] The complete application-test checklist passes.
- [ ] The representative audio matrix has been executed.
- [ ] WER/CER/timestamp/DER baselines have been recorded.
- [x] A 60-minute file completes on RTX 3090 without OOM.
- [x] A batch of at least ten files shows no accumulating VRAM use.
- [ ] SRT and VTT have been reviewed manually in a private YouTube upload.

## Security and reliability

- [x] Offline tests perform no network requests.
- [x] Tokens do not occur in logs or results.
- [x] Failed jobs do not create final results JSON files.
- [x] Existing files are never overwritten.
- [x] `clean` does not remove final results or models.
- [x] Locking prevents concurrent output collisions.

## Distribution

- [ ] A clean installation on WSL2 Ubuntu 24.04 is documented and tested.
- [x] The lockfile is approved.
- [ ] CLI documentation matches `--help`.
- [x] Known limitations are listed in README or release notes.
- [x] Application version and schema version are defined.
