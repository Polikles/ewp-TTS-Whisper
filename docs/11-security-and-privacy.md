# Security and Privacy

## 1. Threat model

The application may process unpublished podcasts, training recordings, and personal data. Primary risks include:

- accidental upload to an external service;
- exposure of the Hugging Face token;
- leaving audio in temporary directories;
- overwriting results;
- writing full transcript text to logs;
- following symbolic links outside the intended input directory;
- concurrent writes to the same result.

## 2. Requirements

- the MVP pipeline runs locally;
- transcription performs no network requests in offline mode;
- no telemetry;
- `HF_TOKEN` is read only from an environment variable or a future secure GUI store;
- the token is never serialized;
- default logs do not contain transcript content;
- the work directory is private to the current user;
- symbolic links are not followed by default;
- final files are never overwritten;
- temporary files preserved after failure are reported to the user and can be removed explicitly.

## 3. Network use

Permitted network operations are separated from transcription:

- explicit model downloads;
- future update checks only with consent and outside the MVP.

`transcribe` in offline mode should configure libraries so that missing models cannot be downloaded implicitly.

## 4. Paths in JSON

`results.json` stores source paths for reproducibility. Paths may themselves be sensitive, and user documentation must state this clearly.

A future publication/redaction mode may remove or pseudonymize paths from shared copies, but the canonical local MVP result retains them.

## 5. Supply chain

- installation from a lockfile;
- preference for official sources;
- no automatic prerelease use;
- vulnerability scanning in CI;
- dependency upgrades in dedicated pull requests with audio-quality regression tests;
- backend versions recorded in every result.
