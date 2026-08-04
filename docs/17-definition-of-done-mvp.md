# Definition of Done — MVP

The MVP is complete when the following conditions are met.

## Functionality

- [ ] All FR requirements are implemented or explicitly deferred through an ADR.
- [ ] `doctor`, `inspect`, `dry-run`, `transcribe`, `export`, and `clean` work.
- [ ] A results JSON is always generated after successful transcription.
- [ ] TXT, SRT, VTT, and optional segments JSON are generated without running ASR again.
- [ ] Single file, directory batch, grouped files, dual mono, and split speakers work.
- [ ] Diarization works for mixed mono/stereo.
- [ ] SHA-256/signature-based skipping and versioning work.

## Quality

- [ ] All examples pass JSON Schema validation.
- [ ] The complete application-test checklist passes.
- [ ] The representative audio matrix has been executed.
- [ ] WER/CER/timestamp/DER baselines have been recorded.
- [x] A 60-minute file completes on RTX 3090 without OOM.
- [x] A batch of at least ten files shows no accumulating VRAM use.
- [ ] SRT and VTT have been reviewed manually in a private YouTube upload.

## Security and reliability

- [ ] Offline tests perform no network requests.
- [ ] Tokens do not occur in logs or results.
- [ ] Failed jobs do not create final results JSON files.
- [ ] Existing files are never overwritten.
- [ ] `clean` does not remove final results or models.
- [ ] Locking prevents concurrent output collisions.

## Distribution

- [ ] A clean installation on WSL2 Ubuntu 24.04 is documented and tested.
- [ ] The lockfile is approved.
- [ ] CLI documentation matches `--help`.
- [ ] Known limitations are listed in README or release notes.
- [ ] Application version and schema version are defined.
