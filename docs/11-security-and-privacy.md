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

### Future correction and translation APIs

Cloud LLM/API use is never an offline operation. It must be explicitly selected and must
show a clear data-transfer warning before transcript content leaves the machine. In an
interactive session the choices are: reject and continue without the cloud operation,
accept once, or accept persistently. Persistent consent is scoped to the exact provider,
endpoint, operation class, and warning-policy version; changing any of them prompts
again. Non-interactive use requires an explicit consent flag or matching stored consent
and must never infer acceptance.

A loopback/local LLM API is preferable for privacy but is still a separate process and
API boundary. The application cannot guarantee what that server logs, retains, or
forwards. Local API use therefore displays a distinct warning with the same reject,
accept-once, and scoped persistent-consent choices. Documentation must not call a local
API bulletproof or equate it with an in-process offline model.

Strict offline mode blocks cloud endpoints. Secrets and consent records must never be
written to canonical results, logs, audits, or revision content. Revision provenance may
record provider/model/endpoint kind and a non-secret endpoint identity.

## 4. Paths in JSON

`results.json` stores source paths for reproducibility. Paths may themselves be sensitive, and user documentation must state this clearly.

A future publication/redaction mode may remove or pseudonymize paths from shared copies, but the canonical local MVP result retains them.

## 5. Supply chain

- installation from a lockfile;
- preference for official sources;
- no automatic prerelease use;
- local vulnerability scanning as part of the release gate;
- dependency upgrades in dedicated pull requests with audio-quality regression tests;
- backend versions recorded in every result.
