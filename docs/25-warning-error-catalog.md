# Warning and error code catalogue

Every expected user-visible diagnostic has a stable uppercase code. Human CLI output uses
`WARNING [CODE]: message` or `Error [CODE]: message`; Typer argument errors use
`CODE: message` inside its standard usage panel. Batch records use the same code without
brackets. The prose may improve between versions, but a code's meaning must not be silently
reassigned.

Warnings do not by themselves make an artifact final or invalid. Errors stop the affected
operation; directory batches may continue with other jobs. Unexpected programming defects
may still produce a traceback and are not assigned a misleading expected-error code.

## Input, audio, and transcript warnings

| Code | Meaning and likely cause | Safety implication | Operator action |
|---|---|---|---|
| `INPUT_FILENAME_WHITESPACE` | An input filename contains whitespace. | Processing is unchanged, but shell quoting is easier to get wrong. | Quote paths and consider simpler names for automation. |
| `INPUT_DURATION_MISMATCH` | Grouped sources differ in duration beyond the warning threshold. | Alignment or speaker merging may be incomplete. | Verify that the files belong to one episode. |
| `CHANNEL_CLASSIFICATION_AMBIGUOUS` | Channel evidence cannot distinguish a safe topology. | Automatic channel selection may omit or duplicate speech. | Inspect the media and select `--channel-mode` explicitly. |
| `CHANNEL_MODE_OVERRIDE_IMPLAUSIBLE` | The requested channel mode conflicts with measured audio. | The explicit override is honored but may produce poor output. | Recheck the channel topology before publication. |
| `AUDIO_CLIPPING` | Samples repeatedly reach the digital ceiling. | Speech recognition may lose clipped phonemes. | Prefer an unclipped source when available. |
| `AUDIO_LOW_LEVEL` | The analyzed signal is unusually quiet. | ASR and diarization quality may fall. | Verify the source or normalize it outside the immutable workflow. |
| `AUDIO_CHANNEL_IMBALANCE` | Stereo channel levels differ substantially. | One speaker or channel may be underrepresented. | Inspect channels and choose the correct topology. |
| `AUDIO_HIGH_SILENCE_RATIO` | Much of the analyzed material is inactive. | Processing is valid but runtime and segmentation may be inefficient. | Confirm that the selected stream is the intended recording. |
| `EXISTING_RESULT_SKIPPED` | An exact episode signature already has a result. | No output was overwritten. | Reuse it or pass `--force` for a new immutable version. |
| `SOURCE_NAME_COLLISION` | The job name exists for different source content. | A new version is allocated; similarly named files may be confused. | Verify the selected input and resulting version. |
| `WORD_ALIGNMENT_MISSING` | Alignment produced no usable word timestamp for part of the text. | Timing-dependent exports are less precise. | Review the affected text against audio. |
| `WORD_TIMESTAMP_INTERPOLATED` | A missing word timestamp was reconstructed from neighbors. | Text remains available, but the inferred timing is approximate. | Check subtitle timing around the warning. |
| `SPEAKER_ASSIGNMENT_MISSING` | No diarization turn owned a word. | Speaker attribution is incomplete. | Review and correct speaker assignment manually. |
| `SPEAKER_ASSIGNMENT_AMBIGUOUS` | More than one speaker assignment was similarly plausible. | The selected speaker may be wrong. | Compare the affected interval with audio. |

## Review, correction, and translation warnings

| Code | Meaning and likely cause | Safety implication | Operator action |
|---|---|---|---|
| `REVISION_ALIGNMENT_AMBIGUOUS` | A revision anchor has multiple equally good alignments. | The candidate text is non-final and may attach to the wrong occurrence. | Review the named anchor against source and audio. |
| `REVISION_INSERT_ACROSS_LONG_GAP` | Inserted text spans an unusually long timing gap. | Subtitle timing may not represent the spoken location. | Review timing and split or relocate the edit manually. |
| `PROVIDER_SOURCE_ENVELOPE_DISCARDED` | LM Studio repeated source-envelope fields around a usable target. | Compatibility parsing succeeded, but provider adherence was imperfect. | Manually review the unit. |
| `PROVIDER_TRANSLATOR_NOTES_DISCARDED` | A known translator-notes field accompanied a usable target. | Notes were not accepted into the artifact. | Manually review the named unit. |
| `AUTOMATED_CORRECTION_NON_FINAL` | Automated correction is producing a review candidate. | It is not verified publication text. | Complete manual review and apply an accepted child revision. |
| `AUTOMATED_TRANSLATION_NON_FINAL` | Automated translation is producing a review candidate. | Meaning, names, or conventions may be wrong. | Perform comprehensive manual semantic review. |
| `TRANSLATION_SOURCE_UNREVIEWED` | Translation uses an automated Polish candidate rather than a verified revision. | Source errors can propagate into the translation. | Verify both source and target before acceptance. |
| `EXTERNAL_API_DATA_DISCLOSURE` | Transcript text will be sent to a separate API process or cloud provider. | That process may log, retain, or forward text. | Confirm provider policy and grant consent only for the exact scope. |
| `REMOTE_API_TRANSPORT_UNVERIFIED` | A non-loopback local API endpoint is used. | The application cannot guarantee transport confidentiality. | Use a trusted encrypted network or a loopback endpoint. |

## Expected application errors

| Code | Meaning and likely cause | Safety implication | Operator action |
|---|---|---|---|
| `APPLICATION_ERROR` | A controlled application failure used no narrower subtype. | The operation stopped before successful publication. | Read the message and preserve diagnostics for a bug report. |
| `MISSING_CAPABILITY` | A required executable, model, GPU feature, or runtime capability is absent. | The requested stage cannot run safely. | Run `doctor` and follow its setup guidance. |
| `INVALID_CONFIGURATION` | TOML or merged configuration is unreadable or invalid. | Defaults are not silently substituted. | Correct the reported setting or use a known-good config. |
| `INPUT_NOT_FOUND` | The selected path does not exist. | No processing occurred. | Re-export shell variables and verify the exact path. |
| `UNSUPPORTED_INPUT` | The direct input is not a supported regular file or directory. | No unsupported content is guessed. | Select a supported media file or directory. |
| `SYMLINK_INPUT` | A direct symlink was supplied where the safety policy forbids it. | The application avoids resolving an unexpected target. | Select the real intended path explicitly. |
| `MEDIA_PROBE_FAILED` | ffprobe could not read valid media metadata. | Stream selection cannot be trusted. | Verify the file and ffprobe installation. |
| `NO_AUDIO_STREAM` | The selected media contains no supported audio stream. | Transcription cannot proceed. | Choose media with audio or the correct stream. |
| `AUDIO_PREPARATION_FAILED` | FFmpeg could not create the controlled working audio. | ASR did not receive a trusted input. | Check FFmpeg output, permissions, space, and media integrity. |
| `CHANNEL_ANALYSIS_FAILED` | Channel samples could not be analyzed. | Automatic topology selection is unavailable. | Inspect the source and FFmpeg readiness. |
| `AMBIGUOUS_GROUP` | Filename grouping produced more than one plausible episode. | Files are not combined by guesswork. | Use an explicit `--group` and `--group-id`. |
| `MULTIPLE_AUDIO_STREAMS` | Media has multiple audio streams without an explicit choice. | The application refuses to pick possibly wrong audio. | Inspect streams and select the intended one. |
| `SAMPLE_RATE_MISMATCH` | Explicitly grouped sources have incompatible sample rates. | Their timelines cannot be merged safely. | Supply matching sources or preprocess copies separately. |
| `DURATION_MISMATCH` | Grouped duration drift exceeds the hard limit. | Merging could misattribute or omit speech. | Verify the group; override only after manual inspection. |
| `TRANSCRIPT_NORMALIZATION_FAILED` | Engine output cannot form a valid ordered canonical timeline. | No malformed result is published. | Preserve work files and inspect backend output. |
| `UNSUPPORTED_PIPELINE_SCOPE` | The requested media topology or operation is outside the implemented contract. | The application does not apply an unsafe fallback. | Use a supported workflow or follow the cited roadmap limitation. |
| `SPEECH_ENGINE_ERROR` | ASR, alignment, or diarization failed or returned invalid data. | No successful canonical result is published. | Check models, GPU/runtime readiness, and retained work logs. |
| `UNSAFE_OUTPUT_NAME` | A job identifier cannot safely become a filename. | Path traversal or ambiguous output is prevented. | Supply a safe explicit group/job identifier. |
| `INVALID_EXISTING_RESULT` | Existing output metadata is unreadable or inconsistent. | It is not overwritten or treated as valid. | Move the suspect artifact aside and audit it. |
| `INVALID_CANONICAL_RESULT` | Canonical JSON is malformed, incompatible, or the selected path is not a file. | Review/export does not operate on an untrusted source. | Select the exact results JSON; never hand-edit it. |
| `INVALID_REVISION` | A revision is malformed or incompatible with its base/parent. | Wrong-lineage text is not applied or exported. | Supply the exact base and compatible revision. |
| `REVISION_REVIEW_INVALID` | Review structure or protected metadata is invalid. | Machine-owned lineage cannot be trusted. | Recreate the review and edit only permitted text. |
| `REVISION_ANCHOR_INVALID` | An anchor was removed, reordered, duplicated, or malformed. | Text cannot be mapped safely to canonical words. | Restore it or prepare a fresh review. |
| `REVISION_SPEAKER_INVALID` | A speaker directive is malformed or unsupported. | Speaker reassignment is not guessed. | Use a valid stable speaker ID/label. |
| `REVISION_EDITOR_FAILED` | The configured editor failed, was missing, or returned early without a usable edit. | The review remains non-final and is not applied. | Fix `VISUAL`/`EDITOR` or edit the prepared file manually. |
| `INVALID_CORRECTION_RESPONSE` | Provider correction violated the protected chunk contract. | Untrusted model output is rejected. | Retry or use another model; inspect only sanitized diagnostics. |
| `CORRECTION_PROVIDER_ERROR` | A correction provider failed without a narrower classification. | No candidate is published from an untrusted response. | Verify provider configuration and retry deliberately. |
| `CORRECTION_PROVIDER_RETRYABLE` | A transient correction request still failed after bounded retries. | The partial operation remains resumable. | Check connectivity/rate limits, then reuse the resume directory. |
| `CORRECTION_PROVIDER_PERMANENT` | The correction provider rejected a non-retryable request. | Repeating unchanged input is avoided. | Fix endpoint, model, key, or request settings first. |
| `CORRECTION_CONSENT_REQUIRED` | The exact external API scope lacks authorization. | Transcript text was not sent. | Pass `--consent once`/`persist` after reviewing the warning. |
| `INVALID_TRANSLATION` | A translation/review is malformed or incompatible with its source. | Wrong-lineage target text is not published. | Use the exact canonical result, revision, and parent translation. |
| `INVALID_TRANSLATION_RESPONSE` | Automated target output violated the per-unit contract. | Malformed or cross-unit content is rejected. | Retry/resume or choose a more compatible model/output mode. |
| `TRANSLATION_PROVIDER_ERROR` | A translation provider failed without a narrower classification. | No candidate is published from untrusted output. | Verify provider settings and retry deliberately. |
| `TRANSLATION_PROVIDER_UNAVAILABLE` | LM Studio or the selected endpoint is unreachable. | The command fails at preflight instead of waiting through unit retries. | Start the server and verify `/v1/models`. |
| `TRANSLATION_MODEL_UNAVAILABLE` | The requested model is not advertised by the endpoint. | Requests are not sent to an unintended model. | Load it or copy the exact advertised model ID. |
| `TRANSLATION_PROVIDER_RETRYABLE` | A transient translation request exhausted bounded retries. | Valid completed units remain resumable. | Restore service and reuse the same resume directory. |
| `TRANSLATION_PROVIDER_PERMANENT` | A translation request failed permanently. | Futile retries are avoided. | Correct provider/model/output-mode settings. |
| `TRANSLATION_PROVIDER_HTTP_REJECTED` | The provider returned a permanent HTTP status. | Response content stays sanitized. | Use the reported status to check endpoint/auth/model settings. |
| `OUTPUT_LOCK_UNAVAILABLE` | Another process holds the output-directory lock. | Concurrent publication is prevented. | Wait or select another output directory. |
| `OUTPUT_RESERVATION_FAILED` | A planned immutable output/state name could not be reserved. | Existing files are not overwritten. | Inspect collisions and retry with correct directories. |
| `INVALID_JOB_STATE` | A persisted running/terminal state cannot be trusted or transitioned. | Resume/publication stops safely. | Preserve state for audit and start a fresh work root if needed. |
| `UNSAFE_WORK_DIRECTORY` | Work-directory ownership/marker/path checks failed. | Cleanup does not remove uncertain data. | Inspect the path and remove it manually only when ownership is known. |
| `TRANSCRIPTION_FAILED` | A batch job raised an unexpected non-application processing error. | That job failed; other jobs may continue. | Preserve logs/work files and report the defect. |
| `USER_CANCELLED` | The operator interrupted the active job. | Partial final publication is prevented. | Resume or rerun when ready. |

## Command and reporting errors

| Code | Meaning and likely cause | Safety implication | Operator action |
|---|---|---|---|
| `GUI_START_FAILED` | The loopback listener or an allowed-root configuration could not be initialized. | The browser service did not start. | Check the port, directory existence/type, and permissions, then retry. |
| `GUI_HOST_REJECTED` | A browser request used a Host value other than the active loopback endpoint. | DNS-rebinding and unintended virtual-host access are rejected. | Open the exact URL printed by `transcriber gui`. |
| `GUI_ROUTE_NOT_FOUND` | The browser requested an unknown API or asset route. | No filesystem fallback is attempted. | Refresh the bundled frontend; report persistent frontend/backend mismatch. |
| `GUI_ORIGIN_REJECTED` | A POST request did not originate from the active loopback GUI. | Cross-site browser requests cannot invoke application workflows. | Use the exact printed GUI URL rather than another page or proxy. |
| `GUI_REQUEST_INVALID` | A GUI API body is missing, malformed, oversized, or lacks required fields. | The application service is not called with ambiguous input. | Correct the form/request and retry. |
| `GUI_RESPONSE_INVALID` | The frontend received neither a completed result nor a structured error. | The interface does not imply that the operation succeeded. | Preserve the browser console/server state and report the defect. |
| `GUI_PATH_REJECTED` | An input/output path is missing, a symlink, the wrong type, or outside configured roots. | The GUI cannot escape its explicitly granted filesystem scope. | Select a real path under an `--allow-root`; restart with another explicit root if needed. |
| `CLI_USAGE_ERROR` | Typer rejected a missing argument/option, unknown command/option, or invalid declared value. | The command body did not run. | Read the usage panel and command-specific `--help`, then correct the invocation. |
| `CLI_CONSENT_INVALID` | Interactive consent was not `reject`, `once`, or `persist`. | No new consent is granted. | Enter one documented value. |
| `CLI_SPEAKER_COUNT_INVALID` | Speaker count is neither `auto` nor a positive integer. | Invalid diarization settings are rejected. | Correct the option value. |
| `CLI_SPEAKER_MAP_INVALID` | A mapping does not use `SOURCE=NAME`. | Ambiguous labels are not applied. | Correct the mapping syntax. |
| `CLI_SPEAKER_MAP_DUPLICATE` | One source speaker was mapped more than once. | Conflicting labels are rejected. | Keep one mapping per source. |
| `CLI_INPUT_SELECTION_INVALID` | Positional input and explicit grouping were combined. | Selection precedence is not guessed. | Choose one input mode. |
| `CLI_GROUP_TOO_SMALL` | Explicit grouping contains fewer than two files. | A meaningless group is rejected. | Use direct input or provide at least two files. |
| `CLI_GROUP_ID_REQUIRED` | An explicit group has no stable ID. | Unsafe/ambiguous output naming is prevented. | Add `--group-id`. |
| `CLI_GROUP_REQUIRED` | `--group-id` was provided without grouped files. | The unused ID is rejected. | Add repeated `--group` options or remove the ID. |
| `CLI_INPUT_REQUIRED` | Neither direct input nor an explicit group was supplied. | No implicit path is selected. | Provide one input mode. |
| `CLI_CLEAN_MODE_INVALID` | Cleanup received both or neither of `--dry-run` and `--yes`. | Deletion never occurs without one explicit mode. | Preview first, then rerun with `--yes`. |
| `CLI_SPEAKER_LABEL_EMPTY` | The one-speaker label is blank. | Empty visible identity is rejected. | Supply a non-empty label. |
| `CLI_SPEAKER_INPUT_INVALID` | A one-speaker label was requested for a directory/group. | One label is not silently applied to multiple sources. | Use a single file or speaker mappings. |
| `CLI_SPEAKER_COUNT_CONFLICT` | `--speaker` conflicts with a count other than one. | Contradictory attribution is rejected. | Use `--speaker-count 1` or remove `--speaker`. |
| `CORRECTION_DICTIONARY_PROPOSAL_FAILED` | Proposal inputs, prior decisions, or output path are invalid. | No partial proposal is published. | Correct the reported corpus/path problem. |
| `CORRECTION_DICTIONARY_APPROVAL_FAILED` | Proposal review is incomplete/invalid or output exists. | Pending mappings are never activated. | Resolve every decision and choose a new immutable output. |
| `TRANSLATION_BENCHMARK_PREPARE_FAILED` | Candidate/gold lineage cannot form assessments. | Incompatible artifacts are not compared. | Correct directories and exact lineage. |
| `TRANSLATION_BENCHMARK_REPORT_FAILED` | Assessments are pending, inconsistent, or unreadable. | No misleading aggregate is emitted. | Complete and validate every assessment. |
| `TRANSLATION_OPERATIONS_REPORT_FAILED` | Translation resume evidence is missing or invalid. | Operational metrics are not guessed. | Select the exact resume directory. |
| `CORRECTION_BENCHMARK_BUILD_FAILED` | Canonical/candidate/gold inputs cannot form a manifest. | Incompatible cases are excluded by failure. | Correct the exact-hash directories. |
| `CORRECTION_BENCHMARK_REPORT_FAILED` | The correction manifest or referenced artifacts are invalid. | No misleading quality score is emitted. | Rebuild or repair the private bundle. |
| `CORRECTION_BENCHMARK_REVIEW_FAILED` | Unsupported-edit review cannot be created safely. | Existing private review files are not overwritten. | Select a valid manifest and fresh `/tmp` output. |
| `CORRECTION_OPERATIONS_REPORT_FAILED` | Correction resume evidence is missing or invalid. | Token/cost/latency values are not guessed. | Select the exact resume directory. |
| `AUTOMATED_TRANSLATION_REQUEST_INVALID` | CLI options cannot form one automated translation request. | No ambiguous provider request is sent. | Correct the reported model/path/mode combination. |
| `TRANSLATION_PREPARE_FAILED` | Translation-review preparation options or source selection conflict. | No misleading review lineage is written. | Correct the source/parent selection. |

## Maintenance rule

New user-visible warnings and expected errors must add a code here in the same change as the
implementation and tests. Tests verify that expected exception classes have valid stable codes
and that codes emitted directly by the CLI are present in this catalogue. Removing or renaming
a code is a compatibility change and requires an explicit migration note.
