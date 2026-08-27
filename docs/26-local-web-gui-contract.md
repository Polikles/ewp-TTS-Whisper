# Local browser GUI contract

## 1. Scope

The graphical interface is one local web application served by EWP Transcriber and opened
in a normal browser. The same frontend assets, versioned API contract, application services,
and persisted artifacts MUST be used on WSL2, bare-metal Ubuntu, and the future Docker image.
Environment-specific launchers, filesystem roots, and Docker mounts MAY differ; behavior and
appearance MUST NOT fork by deployment environment.

The initial GUI is a single-user local tool. Multi-user hosting, public Internet exposure,
remote administration, and account management are outside the first implementation slice.

## 2. Architectural boundary

The browser talks to a local Python web adapter through a versioned `/api/v1` interface. The
adapter MUST call the existing application services directly. It MUST NOT execute
`transcriber` CLI commands as subprocesses, maintain a second transcript/translation model,
or rewrite immutable artifacts in place.

The web adapter owns only presentation concerns, request validation, job orchestration, and
serialization. Canonical results, revisions, translations, dictionaries, audits, and exports
retain their existing schemas, lineage, allocation, validation, and atomic-publication rules.

The packaged frontend MUST be self-contained. Runtime CDNs, telemetry, remote fonts, and
externally hosted JavaScript or CSS are prohibited. Once models are explicitly installed,
local workflows MUST remain usable without Internet access.

## 3. Deployment parity

All supported environments MUST render the same bundled frontend and report the same
application and API versions:

- WSL2 runs the service inside Linux and opens it from a Windows browser;
- bare-metal Ubuntu runs the same service and assets locally;
- the future Docker image runs the same service and assets with explicitly mounted input,
  project, and output directories.

The server binds to loopback by default. The initial GUI MUST NOT offer an unauthenticated
remote-listen shortcut. Any later non-loopback mode requires a separate threat model,
authentication, transport-security, and deployment decision. Docker instructions MUST bind
published ports to loopback unless the later remote-access contract explicitly supersedes
this rule.

## 4. Filesystem interaction

Media files can be large and already exist on the server-visible filesystem. The primary GUI
workflow therefore selects or enters server-side files and directories within configured
allowed roots; it does not upload or duplicate media through the browser.

The web adapter MUST:

- expose only explicitly configured roots and never provide a general filesystem browser;
- normalize paths through the existing path policy and reject traversal or disallowed
  symlink resolution;
- show the resolved source and destination before a mutating or expensive operation;
- preserve Unicode and spaces, and normalize Windows drive, WSL-mounted Windows, and native
  Linux path forms before enforcing the same explicit allowed-root boundary;
- require explicit Docker mounts rather than implying that host paths are automatically
  visible inside a container;
- never serve arbitrary source files as static web content.

Browser upload MAY be designed later as an opt-in convenience, but it is not required for
the initial GUI.

## 5. Required workflow coverage

The GUI MUST eventually expose the same supported pipeline as the application core:

1. inspect and dry-run input selection, grouping, streams, warnings, and output plan;
2. transcribe and monitor a deterministic local job queue;
3. optionally create an LLM-assisted correction candidate;
4. manually review, preview, and apply a transcript revision;
5. export raw or verified transcript artifacts without rerunning ASR;
6. create a manual or LLM-assisted translation from an explicitly identified source;
7. manually review, preview, apply, audit, and export translation artifacts.

Planning controls SHOULD expose language and speaker count per selected file. Values inferred
or supplied by the GUI rather than explicitly chosen by the operator MUST be labeled as
automatic. A later auto-discovery option may use only ephemeral within-job speaker features,
as constrained by the roadmap; it must not create cross-recording identities.

The interface MUST clearly distinguish canonical ASR output, automated non-final candidates,
manually verified revisions, and final/manual translations. Translation from an unreviewed
candidate remains allowed only with the existing warning and exact source provenance.

Project dictionaries MUST be selectable by project, language, version, and hash. The GUI
MUST display the dictionary provenance recorded by an artifact, including `none`. Dictionary
proposal/review management may arrive after the first vertical slice, but must reuse the
existing project-scoped formats and retained approved/rejected decisions.

## 6. Review and media interaction

The transcript editor MUST present human-readable speaker turns while preserving the same
machine-owned anchors and exact lineage used by `EWP-REVIEW 1`. Anchors and metadata may be
hidden visually, but the GUI MUST NOT discard or invent them. Applying changes requires a
preview produced by the existing revision validation/alignment path and an explicit user
action.

Preview is a non-publishing validation step: it parses the exact saved review, verifies its
base hash and protected anchors, runs alignment, and reports revision statistics and warnings
without writing a revision. The GUI MUST label that state as unpublished and show a readable
summary before offering expandable technical JSON. Preparing another review while one is open
MUST require an explicit clear action so unsaved editor content cannot be replaced. Disabled
Apply and Export actions MUST be visually distinct and explain their prerequisite.

Long reviews MUST support both a sequential previous/next-section view and a continuous
all-sections view, with the presentation preference retained locally. A visible speaker block
can be reassigned as a whole in the initial slice. Later editing MUST also permit a reviewer to
split at a word or sentence boundary and reassign only the affected part while retaining exact
lineage. It MUST permit project/revision-scoped speaker display-name replacement when canonical
speaker labels are absent or wrong; neither feature may silently rewrite canonical results.

Equivalent rules apply to translation units: source text remains visible, target text is
editable, source ownership is immutable, and apply uses the existing translation service.

Where source media is available, the GUI SHOULD provide synchronized playback, seeking from
a transcript unit, active-unit highlighting, keyboard operation, and independently persistent
follow-playback and light/dark preferences. Minor source timing inaccuracies are evidence for
later timing work, not permission for the GUI to silently alter canonical timing.

## 7. Jobs, diagnostics, and recovery

The initial scheduler runs at most one GPU-intensive job at a time. Queued work has an
explicit state, operation identity, progress summary, cancellation behavior, and recoverable
resume location. Refreshing or closing the browser MUST NOT corrupt an active operation.

Every expected warning and error displayed by the GUI MUST include its stable diagnostic
code, readable message, and an action/help link into the warning and error catalogue. Provider
availability SHOULD be checked before a long operation so an unreachable backend fails within
a short bounded preflight budget rather than exhausting per-unit retries.

## 8. Privacy and security

The GUI MUST preserve the CLI privacy boundary and consent model:

- transcript content crosses a local-API or cloud boundary only after endpoint
  classification and explicit scoped consent;
- audio is never sent to correction or translation providers;
- credentials are accepted as password-like session input or inherited from the server
  process environment;
- credentials MUST NOT enter URLs, browser history, local storage, logs, artifacts, job
  records, or rendered exception details;
- strict-offline mode blocks all provider calls regardless of UI state;
- provider and non-final-candidate warnings are displayed before execution, not only after.

The server MUST validate host/origin for browser requests, protect state-changing requests
against cross-site request forgery, escape all transcript/provider text, use a restrictive
content-security policy, and expose downloads only through validated artifact identities.
The frontend and backend MUST reject incompatible API versions rather than operating
partially.

## 9. Accessibility and presentation

The interface MUST support keyboard navigation, visible focus, semantic labels, sufficient
contrast, browser zoom, and light/dark presentation. Status MUST NOT be conveyed by color
alone. Destructive or irreversible-looking actions require plain-language scope and outcome,
even when the underlying operation is non-destructive.

The interactive GUI may require JavaScript. If scripts are unavailable, the served page MUST
remain safe and readable and explain that the application requires JavaScript; this does not
weaken the separate no-script readability requirement for exported HTML transcripts.

The About surface MUST show application and API versions, license/warranty information, and
the canonical source-code and issue-tracker links.

## 10. Initial implementation sequence

The smallest acceptable vertical slices are:

1. loopback server, bundled shell, health/version compatibility, allowed-root configuration,
   coded diagnostics, About/license/source surfaces, and automated security tests;
2. inspect/dry-run plus a persistent-in-process job view without GPU execution;
3. transcription scheduling and result discovery;
4. transcript review/preview/apply and model-free export;
5. correction and translation provider workflows with consent and credential handling;
6. dictionary proposal/review management and remaining operator conveniences;
7. package/install qualification on WSL2 and Ubuntu, followed later by the same application
   inside the Docker distribution.

Docker packaging is intentionally downstream. GUI behavior is qualified before container
construction so the container does not become a separate product implementation.
