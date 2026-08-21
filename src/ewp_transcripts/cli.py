"""Terminal adapter for EWP-transcripts."""

import json
import sys
from contextlib import nullcontext, redirect_stdout
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, cast

import typer

from ewp_transcripts.application import (
    BatchExportOutcome,
    BatchReviewPreparationOutcome,
    BatchRevisionOutcome,
    BatchTranscriptionOutcome,
    BatchTranslationExportOutcome,
    BatchTranslationOutcome,
    ExportFormat,
    TranscriptionOutcome,
    TranslationExportFormat,
    application_version,
    apply_correction,
    apply_review_file,
    apply_translation_review_file,
    audit_revision_file,
    audit_translation_file,
    clean_all_workdirs,
    doctor,
    dry_run,
    export_batch,
    export_result,
    export_translation,
    export_translation_batch,
    inspect_input,
    prepare_review_batch,
    prepare_review_file,
    prepare_translation_review_batch,
    prepare_translation_review_file,
    preview_correction,
    preview_review_file,
    preview_translation_review_file,
    process_review_batch,
    process_translation_review_batch,
    transcribe_batch,
    transcribe_one,
)
from ewp_transcripts.config import ApplicationConfig, load_config
from ewp_transcripts.correction_benchmark import (
    build_correction_benchmark_bundle,
    evaluate_correction_benchmark,
    load_correction_benchmark_manifest,
)
from ewp_transcripts.correction_consent import (
    REMOTE_LOCAL_API_WARNING,
    ConsentChoice,
    CorrectionConsentScope,
    correction_api_warning,
    load_correction_consents,
)
from ewp_transcripts.correction_providers import create_correction_provider
from ewp_transcripts.correction_state import summarize_correction_resume_state
from ewp_transcripts.discovery import normalize_input_path
from ewp_transcripts.domain import JobOutputPlan, TranscriptRevision
from ewp_transcripts.domain.correction import CorrectionProvider
from ewp_transcripts.domain.enums import ChannelMode, LanguageMode, PlanDecision
from ewp_transcripts.domain.errors import (
    ApplicationError,
    InvalidCanonicalResultError,
    InvalidConfigurationError,
    MissingCapabilityError,
    OutputLockUnavailableError,
    OutputReservationError,
)
from ewp_transcripts.domain.translation import TranscriptTranslation, TranslationStyle
from ewp_transcripts.lm_studio_adapter import is_loopback_endpoint
from ewp_transcripts.revision_editor import open_review_in_editor, require_review_change

app = typer.Typer(
    name="transcriber",
    help=(
        "Local-first transcription for edited podcast and training recordings. "
        "Run 'transcriber COMMAND --help' for command-specific options."
    ),
    no_args_is_help=True,
)
revise_app = typer.Typer(
    name="revise",
    help=(
        "Prepare, validate, and publish transcript corrections without source audio. "
        "Run 'transcriber revise COMMAND --help' for command-specific options."
    ),
    no_args_is_help=True,
)
benchmark_app = typer.Typer(
    name="benchmark",
    help="Build and evaluate private, exact-hash benchmark bundles.",
    no_args_is_help=True,
)
correction_benchmark_app = typer.Typer(
    name="correction",
    help="Benchmark automated transcript corrections against manual gold revisions.",
    no_args_is_help=True,
)
translate_app = typer.Typer(
    name="translate",
    help=(
        "Prepare, validate, and publish source-faithful Polish-English translations. "
        "Run 'transcriber translate COMMAND --help' for command-specific options."
    ),
    no_args_is_help=True,
)
app.add_typer(revise_app, name="revise")
app.add_typer(translate_app, name="translate")
app.add_typer(benchmark_app, name="benchmark")
benchmark_app.add_typer(correction_benchmark_app, name="correction")


class RequestedChannelMode(StrEnum):
    """Channel modes users may explicitly request."""

    AUTO = "auto"
    MONO = "mono"
    DUAL_MONO = "dual-mono"
    SPLIT_SPEAKERS = "split-speakers"
    MIXED_STEREO = "mixed-stereo"


class RequestedSpeakerLabels(StrEnum):
    ON_CHANGE = "on-change"
    ALWAYS = "always"
    NEVER = "never"


class RequestedTranslationLanguage(StrEnum):
    POLISH = "pl"
    ENGLISH = "en"


class RequestedTranslationRegister(StrEnum):
    PRESERVE = "preserve"
    FORMAL = "formal"
    INFORMAL = "informal"


class RequestedTranslationDiscourse(StrEnum):
    PRESERVE = "preserve"
    ACADEMIC = "academic"
    GENERAL = "general"


class RequestedSubtitlePreset(StrEnum):
    YOUTUBE = "youtube"


class RequestedPreset(StrEnum):
    ACCURATE = "accurate"


class RequestedLanguage(StrEnum):
    POLISH = "pl"
    ENGLISH = "en"
    AUTO = "auto"


class RequestedTranscribeFormat(StrEnum):
    TXT = "txt"
    SRT = "srt"
    VTT = "vtt"


class CleanTarget(StrEnum):
    ALL_WORKDIRS = "all-workdirs"


@correction_benchmark_app.command("build")
def correction_benchmark_build_command(
    base_directory: Annotated[Path, typer.Argument(help="Directory containing canonical results.")],
    candidate_directory: Annotated[
        Path, typer.Option("--candidate-dir", help="Directory containing one candidate per job.")
    ],
    gold_directory: Annotated[
        Path, typer.Option("--gold-dir", help="Directory containing accepted manual revisions.")
    ],
    output_directory: Annotated[
        Path, typer.Option("--output-dir", help="Private directory for the staged bundle.")
    ],
) -> None:
    """Build a private manifest bundle using the latest compatible manual gold."""

    try:
        manifest = build_correction_benchmark_bundle(
            base_directory=normalize_input_path(base_directory),
            candidate_directory=normalize_input_path(candidate_directory),
            gold_directory=normalize_input_path(gold_directory),
            output_directory=normalize_input_path(output_directory),
        )
        loaded = load_correction_benchmark_manifest(manifest)
    except (OSError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(f"MANIFEST {manifest}")
    typer.echo(f"SUMMARY cases={len(loaded.cases)}")


@correction_benchmark_app.command("report")
def correction_benchmark_report_command(
    manifest_path: Annotated[Path, typer.Argument(help="Exact-hash correction manifest.")],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", help="Write the content-free JSON report to this path."),
    ] = None,
) -> None:
    """Evaluate canonical, candidate, and manual-gold lexical differences."""

    try:
        manifest = load_correction_benchmark_manifest(normalize_input_path(manifest_path))
        report = evaluate_correction_benchmark(manifest)
        serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        normalized_output = _optional_user_path(output_path)
        if normalized_output is not None:
            normalized_output.parent.mkdir(parents=True, exist_ok=True)
            normalized_output.write_text(serialized, encoding="utf-8")
            normalized_output.chmod(0o600)
    except (OSError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    if normalized_output is None:
        typer.echo(serialized, nl=False)
        return
    typer.echo(f"REPORT {normalized_output}")
    aggregate = cast(dict[str, dict[str, object]], report["aggregate"])
    correction = aggregate["lexical_correction"]
    activity = aggregate["revision_activity"]
    typer.echo(
        "SUMMARY "
        f"cases={report['case_count']} "
        f"canonical_gold_wer={cast(float, aggregate['baseline']['wer']):.8f} "
        f"canonical_llm_wer={cast(float, aggregate['source_to_candidate']['wer']):.8f} "
        f"gold_llm_wer={cast(float, aggregate['candidate']['wer']):.8f} "
        f"errors_removed={correction['word_error_reduction']} "
        f"improved={correction['improved_cases']} "
        f"unchanged={correction['unchanged_cases']} "
        f"regressed={correction['regressed_cases']} "
        f"changes={activity['total_changes']} "
        f"warnings={activity['warning_count']} "
        f"speaker_changes={activity['speaker_changes']}"
    )


@correction_benchmark_app.command("operations")
def correction_benchmark_operations_command(
    resume_directory: Annotated[
        Path,
        typer.Argument(help="Private correction resume-state directory."),
    ],
    output_path: Annotated[
        Path | None,
        typer.Option("--output", help="Write the content-free operational JSON report."),
    ] = None,
) -> None:
    """Aggregate requests, retries, latency, tokens, and provider-reported cost."""

    try:
        report = summarize_correction_resume_state(normalize_input_path(resume_directory))
        serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        normalized_output = _optional_user_path(output_path)
        if normalized_output is not None:
            normalized_output.parent.mkdir(parents=True, exist_ok=True)
            normalized_output.write_text(serialized, encoding="utf-8")
            typer.echo(f"REPORT {normalized_output}")
    except (OSError, ValueError, ApplicationError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(
        f"SUMMARY chunks={report['chunks']} requests={report['request_count']} "
        f"retries={report['retries']} elapsed_ms={report['elapsed_ms']} "
        f"input_tokens={report['input_tokens']} output_tokens={report['output_tokens']} "
        f"cost_usd_micros={report['cost_usd_micros']}"
    )


class RequestedCorrectionConsent(StrEnum):
    REJECT = "reject"
    ONCE = "once"
    PERSIST = "persist"


class RequestedCorrectionProvider(StrEnum):
    LM_STUDIO = "lm-studio"
    OPENROUTER = "openrouter"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(application_version())
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the application version and exit.",
        ),
    ] = None,
) -> None:
    """Run EWP-transcripts commands."""


def _review_batch_json(outcome: BatchReviewPreparationOutcome) -> str:
    return json.dumps(
        {
            "output_directory": str(outcome.output_directory),
            "prepared": outcome.prepared,
            "failed": outcome.failed,
            "stopped_early": outcome.stopped_early,
            "jobs": [
                {
                    "result_path": str(job.result_path),
                    "status": job.status,
                    "review_path": str(job.review_path) if job.review_path else None,
                    "failure_code": job.failure_code,
                    "failure_message": job.failure_message,
                }
                for job in outcome.jobs
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def _translation_json(
    translation: TranscriptTranslation, *, translation_path: Path | None = None
) -> str:
    payload = translation.model_dump(mode="json", by_alias=True)
    payload["translation_path"] = str(translation_path) if translation_path else None
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _print_translation_preview(translation: TranscriptTranslation) -> None:
    typer.echo(f"PREVIEW {translation.job_id} {translation.direction.target_language}")
    typer.echo(
        f"SUMMARY units={translation.statistics.unit_count} "
        f"source_tokens={translation.statistics.source_tokens} "
        f"target_tokens={translation.statistics.target_tokens} "
        f"warnings={len(translation.warnings)}"
    )


def _print_translation_batch(outcome: BatchTranslationOutcome) -> None:
    for job in outcome.jobs:
        typer.echo(f"{job.status.upper()} {job.input_path}")
        if job.review_path is not None and job.status == "prepared":
            typer.echo(f"  REVIEW {job.review_path}")
        if job.translation_path is not None:
            typer.echo(f"  TRANSLATION {job.translation_path}")
        if job.failure_code is not None:
            typer.echo(f"  ERROR {job.failure_code}: {job.failure_message}")
    typer.echo(
        f"SUMMARY prepared={outcome.count('prepared')} "
        f"previewed={outcome.count('previewed')} applied={outcome.count('applied')} "
        f"failed={outcome.count('failed')} "
        f"stopped_early={str(outcome.stopped_early).lower()}"
    )


def _print_translation_export_batch(outcome: BatchTranslationExportOutcome) -> None:
    for job in outcome.jobs:
        typer.echo(f"{job.status.upper()} {job.translation_path}")
        if job.outcome is not None:
            for path in job.outcome.written:
                typer.echo(f"  WROTE {path}")
            for path in job.outcome.skipped:
                typer.echo(f"  SKIPPED {path}")
        if job.failure_code is not None:
            typer.echo(f"  ERROR {job.failure_code}: {job.failure_message}")
    typer.echo(
        f"SUMMARY exported={outcome.exported} failed={outcome.failed} "
        f"stopped_early={str(outcome.stopped_early).lower()}"
    )


@translate_app.command("prepare")
def translate_prepare_command(
    result_path: Annotated[
        Path,
        typer.Argument(help="Exact canonical result to translate.", metavar="RESULT_JSON"),
    ],
    target_language: Annotated[
        RequestedTranslationLanguage,
        typer.Option("--target-language", help="Target language: pl or en."),
    ],
    revision_path: Annotated[
        Path | None,
        typer.Option("--revision", help="Exact compatible source transcript revision."),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Include canonical results in subdirectories."),
    ] = False,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write EWP-TRANSLATION review files here."),
    ] = None,
    register: Annotated[
        RequestedTranslationRegister,
        typer.Option("--register", help="Preserve, formalize, or informalize register."),
    ] = RequestedTranslationRegister.PRESERVE,
    discourse: Annotated[
        RequestedTranslationDiscourse,
        typer.Option("--discourse", help="Preserve, academic, or general discourse."),
    ] = RequestedTranslationDiscourse.PRESERVE,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
) -> None:
    """Publish an editable review whose target lines begin blank."""

    try:
        config = load_config(explicit_path=config_path)
        normalized_result = normalize_input_path(result_path)
        translation_style = TranslationStyle(
            register=register.value,
            discourse=discourse.value,
        )
        if normalized_result.is_dir():
            batch = prepare_translation_review_batch(
                normalized_result,
                target_language=target_language.value,
                config=config,
                revision=revision_path,
                output_directory=_optional_user_path(output_directory),
                recursive=recursive,
                style=translation_style,
            )
        else:
            outcome = prepare_translation_review_file(
                normalized_result,
                target_language=target_language.value,
                config=config,
                revision_path=revision_path,
                output_directory=_optional_user_path(output_directory),
                style=translation_style,
            )
    except (ApplicationError, ValueError) as error:
        if isinstance(error, ApplicationError):
            _expected_error(error)
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=4) from error
    if normalized_result.is_dir():
        _print_translation_batch(batch)
        if batch.count("failed"):
            raise typer.Exit(code=5)
    else:
        typer.echo(f"PREPARED {outcome.path}")
        typer.echo(f"SUMMARY units={len(outcome.review.units)}")


@translate_app.command("preview")
def translate_preview_command(
    review_path: Annotated[
        Path,
        typer.Argument(help="Completed EWP-TRANSLATION review.", metavar="REVIEW"),
    ],
    result_path: Annotated[
        Path,
        typer.Option("--results", help="Exact canonical result used to prepare the review."),
    ],
    revision_path: Annotated[
        Path | None,
        typer.Option("--revision", help="Exact source transcript revision, when used."),
    ] = None,
    revisions_directory: Annotated[
        Path | None,
        typer.Option(
            "--revisions-dir",
            help="Directory containing exact source revisions for a review batch.",
        ),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Include translation reviews in subdirectories."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the unpublished translation as JSON."),
    ] = False,
) -> None:
    """Validate a completed review and exact source without writing an artifact."""

    try:
        normalized_review = normalize_input_path(review_path)
        if normalized_review.is_dir():
            batch = process_translation_review_batch(
                normalized_review,
                config=load_config(),
                results_directory=normalize_input_path(result_path),
                revisions_directory=_optional_user_path(revisions_directory),
                recursive=recursive,
                apply=False,
            )
        else:
            outcome = preview_translation_review_file(
                normalized_review,
                result_path=result_path,
                revision_path=revision_path,
            )
    except ApplicationError as error:
        _expected_error(error)
    if normalized_review.is_dir():
        _print_translation_batch(batch)
        if batch.count("failed"):
            raise typer.Exit(code=5)
    elif json_output:
        typer.echo(_translation_json(outcome.translation))
    else:
        _print_translation_preview(outcome.translation)


@translate_app.command("apply")
def translate_apply_command(
    review_path: Annotated[
        Path,
        typer.Argument(help="Completed EWP-TRANSLATION review.", metavar="REVIEW"),
    ],
    result_path: Annotated[
        Path,
        typer.Option("--results", help="Exact canonical result used to prepare the review."),
    ],
    revision_path: Annotated[
        Path | None,
        typer.Option("--revision", help="Exact source transcript revision, when used."),
    ] = None,
    revisions_directory: Annotated[
        Path | None,
        typer.Option(
            "--revisions-dir",
            help="Directory containing exact source revisions for a review batch.",
        ),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Include translation reviews in subdirectories."),
    ] = False,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write the immutable translation here."),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the translation outcome as JSON."),
    ] = False,
) -> None:
    """Validate and publish a complete immutable manual translation."""

    try:
        config = load_config(explicit_path=config_path)
        normalized_review = normalize_input_path(review_path)
        if normalized_review.is_dir():
            batch = process_translation_review_batch(
                normalized_review,
                config=config,
                results_directory=normalize_input_path(result_path),
                revisions_directory=_optional_user_path(revisions_directory),
                output_directory=_optional_user_path(output_directory),
                recursive=recursive,
                apply=True,
            )
        else:
            outcome = apply_translation_review_file(
                normalized_review,
                result_path=result_path,
                config=config,
                revision_path=revision_path,
                output_directory=_optional_user_path(output_directory),
            )
    except ApplicationError as error:
        _expected_error(error)
    if normalized_review.is_dir():
        _print_translation_batch(batch)
        if batch.count("failed"):
            raise typer.Exit(code=5)
    elif json_output:
        typer.echo(
            _translation_json(
                outcome.translation,
                translation_path=outcome.translation_path,
            )
        )
    else:
        typer.echo(f"APPLIED {outcome.review_path}")
        typer.echo(f"  TRANSLATION {outcome.translation_path}")
        typer.echo(
            f"SUMMARY translation_number={outcome.translation.translation_number} "
            f"units={outcome.translation.statistics.unit_count}"
        )


@translate_app.command("export")
def translate_export_command(
    translation_path: Annotated[
        Path,
        typer.Argument(help="Immutable translation JSON to export.", metavar="TRANSLATION_JSON"),
    ],
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write translated TXT output here."),
    ] = None,
    formats: Annotated[
        list[TranslationExportFormat] | None,
        typer.Option("--format", help="Translated export format; may be repeated."),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Include translation JSON in subdirectories."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
) -> None:
    """Render deterministic UTF-8 TXT from one immutable translation."""

    try:
        config = load_config(explicit_path=config_path)
        normalized_translation = normalize_input_path(translation_path)
        selected_formats = tuple(formats or (TranslationExportFormat.TXT,))
        if normalized_translation.is_dir():
            batch = export_translation_batch(
                normalized_translation,
                config=config,
                formats=selected_formats,
                output_directory=_optional_user_path(output_directory),
                recursive=recursive,
            )
        else:
            outcome = export_translation(
                normalized_translation,
                config=config,
                formats=selected_formats,
                output_directory=_optional_user_path(output_directory),
            )
    except ApplicationError as error:
        _expected_error(error)
    if normalized_translation.is_dir():
        _print_translation_export_batch(batch)
        if batch.failed:
            raise typer.Exit(code=5)
    else:
        for path in outcome.written:
            typer.echo(f"WROTE {path}")
        for path in outcome.skipped:
            typer.echo(f"SKIPPED {path}")


@translate_app.command("audit")
def translate_audit_command(
    translation_path: Annotated[
        Path,
        typer.Argument(help="Immutable translation JSON to audit.", metavar="TRANSLATION_JSON"),
    ],
    results_directory: Annotated[
        Path,
        typer.Option("--results-dir", help="Directory containing the exact canonical result."),
    ],
    revisions_directory: Annotated[
        Path | None,
        typer.Option("--revisions-dir", help="Directory containing the exact source revision."),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write the reconstructed audit here."),
    ] = None,
    no_write: Annotated[
        bool,
        typer.Option("--no-write", help="Validate and print summary without publication."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Print the complete reconstructed audit JSON."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
) -> None:
    """Reconstruct source/target unit evidence and optionally publish it."""

    try:
        outcome = audit_translation_file(
            translation_path,
            config=load_config(explicit_path=config_path),
            results_directory=normalize_input_path(results_directory),
            revisions_directory=_optional_user_path(revisions_directory),
            output_directory=_optional_user_path(output_directory),
            publish=not no_write,
        )
    except ApplicationError as error:
        _expected_error(error)
    if json_output:
        typer.echo(json.dumps(outcome.audit, ensure_ascii=False, indent=2))
        return
    typer.echo(f"AUDIT {outcome.translation_path}")
    if outcome.audit_path is not None:
        typer.echo(f"  {'WROTE' if outcome.written else 'SKIPPED'} {outcome.audit_path}")
    units = outcome.audit["units"]
    assert isinstance(units, list)
    typer.echo(f"SUMMARY units={len(units)} written={int(outcome.written)}")


@revise_app.command("prepare")
def revise_prepare_command(
    input_path: Annotated[
        Path,
        typer.Argument(
            help="Completed canonical result or directory containing results.",
            metavar="INPUT",
        ),
    ],
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write EWP-REVIEW files to this directory."),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Include completed results in subdirectories."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the batch outcome as JSON."),
    ] = False,
) -> None:
    """Create editable EWP-REVIEW files without loading audio or ML models."""

    try:
        config = load_config(explicit_path=config_path)
        outcome = prepare_review_batch(
            input_path,
            config=config,
            output_directory=_optional_user_path(output_directory),
            recursive=recursive,
            anchor_target_words=config.revision.anchor_target_words,
        )
    except ApplicationError as error:
        _expected_error(error)

    if json_output:
        typer.echo(_review_batch_json(outcome))
    else:
        typer.echo(f"Output directory: {outcome.output_directory}")
        for job in outcome.jobs:
            typer.echo(f"{job.status.upper()} {job.result_path}")
            if job.review_path is not None:
                typer.echo(f"  REVIEW {job.review_path}")
            if job.failure_code is not None:
                typer.echo(f"  ERROR {job.failure_code}: {job.failure_message}")
        typer.echo(
            f"SUMMARY prepared={outcome.prepared} failed={outcome.failed} "
            f"stopped_early={str(outcome.stopped_early).lower()}"
        )
    if outcome.failed:
        raise typer.Exit(code=5)


def _revision_json(
    revision: TranscriptRevision,
    *,
    revision_path: Path | None = None,
) -> str:
    payload = revision.model_dump(mode="json")
    payload["revision_path"] = str(revision_path) if revision_path else None
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _print_revision_preview(revision: TranscriptRevision) -> None:
    typer.echo(f"PREVIEW {revision.job_id}")
    typer.echo(
        f"SUMMARY source_tokens={revision.statistics.source_tokens} "
        f"revision_tokens={revision.statistics.revision_tokens} "
        f"warnings={len(revision.warnings)}"
    )


def _revision_batch_json(outcome: BatchRevisionOutcome) -> str:
    return json.dumps(
        {
            "previewed": outcome.previewed,
            "applied": outcome.applied,
            "failed": outcome.failed,
            "stopped_early": outcome.stopped_early,
            "jobs": [
                {
                    "review_path": str(job.review_path),
                    "status": job.status,
                    "revision_path": str(job.revision_path) if job.revision_path else None,
                    "failure_code": job.failure_code,
                    "failure_message": job.failure_message,
                }
                for job in outcome.jobs
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def _print_revision_batch(outcome: BatchRevisionOutcome) -> None:
    for job in outcome.jobs:
        typer.echo(f"{job.status.upper()} {job.review_path}")
        if job.revision_path is not None:
            typer.echo(f"  REVISION {job.revision_path}")
        if job.failure_code is not None:
            typer.echo(f"  ERROR {job.failure_code}: {job.failure_message}")
    typer.echo(
        f"SUMMARY previewed={outcome.previewed} applied={outcome.applied} "
        f"failed={outcome.failed} stopped_early={str(outcome.stopped_early).lower()}"
    )


def _export_batch_json(outcome: BatchExportOutcome) -> str:
    return json.dumps(
        {
            "exported": outcome.exported,
            "failed": outcome.failed,
            "written": outcome.written,
            "skipped": outcome.skipped,
            "stopped_early": outcome.stopped_early,
            "jobs": [
                {
                    "results_path": str(job.results_path),
                    "status": job.status,
                    "revision_path": (
                        str(job.outcome.revision_path)
                        if job.outcome and job.outcome.revision_path
                        else None
                    ),
                    "written": ([str(path) for path in job.outcome.written] if job.outcome else []),
                    "skipped": ([str(path) for path in job.outcome.skipped] if job.outcome else []),
                    "failure_code": job.failure_code,
                    "failure_message": job.failure_message,
                }
                for job in outcome.jobs
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def _print_export_batch(outcome: BatchExportOutcome) -> None:
    for job in outcome.jobs:
        typer.echo(f"{job.status.upper()} {job.results_path}")
        if job.outcome is not None:
            if job.outcome.revision_path is not None:
                typer.echo(f"  REVISION {job.outcome.revision_path}")
            for path in job.outcome.written:
                typer.echo(f"  WROTE {path}")
            for path in job.outcome.skipped:
                typer.echo(f"  SKIP {path}")
        if job.failure_code is not None:
            typer.echo(f"  ERROR {job.failure_code}: {job.failure_message}")
    typer.echo(
        f"SUMMARY exported={outcome.exported} failed={outcome.failed} "
        f"written={outcome.written} skipped={outcome.skipped} "
        f"stopped_early={str(outcome.stopped_early).lower()}"
    )


@revise_app.command("preview")
def revise_preview_command(
    review_path: Annotated[
        Path,
        typer.Argument(
            help="EWP-REVIEW file or directory to validate and align.",
            metavar="REVIEW_OR_DIRECTORY",
        ),
    ],
    results_directory: Annotated[
        Path | None,
        typer.Option("--results-dir", help="Directory containing the exact base result."),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Include review files in subdirectories."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the unpublished revision as JSON."),
    ] = False,
) -> None:
    """Validate and align a review without writing a revision."""

    try:
        config = load_config(explicit_path=config_path)
        normalized_review = normalize_input_path(review_path)
        if normalized_review.is_dir():
            batch = process_review_batch(
                normalized_review,
                config=config,
                results_directory=_optional_user_path(results_directory),
                recursive=recursive,
                apply=False,
            )
        else:
            outcome = preview_review_file(
                normalized_review,
                results_directory=_optional_user_path(results_directory),
                long_gap_warning_ms=config.revision.long_gap_warning_ms,
            )
    except ApplicationError as error:
        _expected_error(error)
    if normalized_review.is_dir():
        if json_output:
            typer.echo(_revision_batch_json(batch))
        else:
            _print_revision_batch(batch)
        if batch.failed:
            raise typer.Exit(code=5)
    elif json_output:
        typer.echo(_revision_json(outcome.revision))
    else:
        _print_revision_preview(outcome.revision)


@revise_app.command("apply")
def revise_apply_command(
    review_path: Annotated[
        Path,
        typer.Argument(
            help="EWP-REVIEW file or directory to validate and apply.",
            metavar="REVIEW_OR_DIRECTORY",
        ),
    ],
    results_directory: Annotated[
        Path | None,
        typer.Option("--results-dir", help="Directory containing the exact base result."),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write the immutable revision to this directory."),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Include review files in subdirectories."),
    ] = False,
    no_apply: Annotated[
        bool,
        typer.Option("--no-apply", help="Run the complete preview path without writing."),
    ] = False,
    audit: Annotated[
        bool,
        typer.Option("--audit", help="Publish detailed diagnostics after a successful apply."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the revision outcome as JSON."),
    ] = False,
) -> None:
    """Validate a review and publish an immutable full-snapshot revision."""

    try:
        config = load_config(explicit_path=config_path)
        normalized_review = normalize_input_path(review_path)
        if normalized_review.is_dir():
            batch = process_review_batch(
                normalized_review,
                config=config,
                results_directory=_optional_user_path(results_directory),
                output_directory=_optional_user_path(output_directory),
                recursive=recursive,
                apply=not no_apply,
            )
        elif no_apply:
            preview = preview_review_file(
                normalized_review,
                results_directory=_optional_user_path(results_directory),
                long_gap_warning_ms=config.revision.long_gap_warning_ms,
            )
            revision = preview.revision
            revision_path = None
        else:
            applied = apply_review_file(
                normalized_review,
                config=config,
                results_directory=_optional_user_path(results_directory),
                output_directory=_optional_user_path(output_directory),
            )
            revision = applied.revision
            revision_path = applied.revision_path
    except ApplicationError as error:
        _expected_error(error)
    audit_path = None
    if (
        not normalized_review.is_dir()
        and (audit or config.revision.generate_audit)
        and revision_path is not None
    ):
        audit_path = audit_revision_file(
            revision_path,
            config=config,
            results_directory=_optional_user_path(results_directory),
            output_directory=_optional_user_path(output_directory),
        ).audit_path
    if normalized_review.is_dir():
        if (audit or config.revision.generate_audit) and not no_apply:
            for job in batch.jobs:
                if job.revision_path is not None:
                    audit_revision_file(
                        job.revision_path,
                        config=config,
                        results_directory=_optional_user_path(results_directory),
                        output_directory=_optional_user_path(output_directory),
                    )
        if json_output:
            typer.echo(_revision_batch_json(batch))
        else:
            _print_revision_batch(batch)
        if batch.failed:
            raise typer.Exit(code=5)
    elif json_output:
        typer.echo(_revision_json(revision, revision_path=revision_path))
    elif revision_path is None:
        _print_revision_preview(revision)
    else:
        typer.echo(f"APPLIED {revision.job_id}")
        typer.echo(f"  REVISION {revision_path}")
        if audit_path is not None:
            typer.echo(f"  AUDIT {audit_path}")
        typer.echo(
            f"SUMMARY revision_number={revision.revision_number} "
            f"revision_tokens={revision.statistics.revision_tokens} "
            f"warnings={len(revision.warnings)}"
        )


@revise_app.command("correct")
def revise_correct_command(
    results_json: Annotated[
        Path,
        typer.Argument(help="Completed canonical result to correct.", metavar="RESULTS_JSON"),
    ],
    source_revision: Annotated[
        Path | None,
        typer.Option(
            "--revision",
            help="Correct this compatible revision and record it as the exact parent.",
        ),
    ] = None,
    provider_name: Annotated[
        RequestedCorrectionProvider,
        typer.Option("--provider", help="Correction API provider: lm-studio or openrouter."),
    ] = RequestedCorrectionProvider.LM_STUDIO,
    model: Annotated[
        str | None,
        typer.Option("--model", help="Exact model identifier exposed by the selected provider."),
    ] = None,
    endpoint: Annotated[
        str | None,
        typer.Option("--endpoint", help="Explicit endpoint for the selected provider."),
    ] = None,
    allow_remote_endpoint: Annotated[
        bool,
        typer.Option(
            "--allow-remote-endpoint",
            help="Explicitly allow a non-loopback LM Studio HTTP(S) endpoint.",
        ),
    ] = False,
    allow_cloud: Annotated[
        bool,
        typer.Option(
            "--allow-cloud",
            help="Disable strict-offline mode for this explicit cloud correction command.",
        ),
    ] = False,
    api_key_env: Annotated[
        str | None,
        typer.Option(
            "--api-key-env",
            help="Environment-variable name containing the OpenRouter API key.",
        ),
    ] = None,
    reasoning_max_tokens: Annotated[
        int | None,
        typer.Option(
            "--reasoning-max-tokens",
            min=0,
            help="OpenRouter reasoning-token budget; 0 disables supported model thinking.",
        ),
    ] = None,
    output_mode: Annotated[
        str | None,
        typer.Option(
            "--output-mode",
            help="Provider response mode: json-schema (default) or explicit json-text fallback.",
        ),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write the immutable revision to this directory."),
    ] = None,
    resume_directory: Annotated[
        Path | None,
        typer.Option("--resume-dir", help="Store private validated per-chunk resume state."),
    ] = None,
    preview: Annotated[
        bool,
        typer.Option("--preview", help="Validate the complete correction without publishing."),
    ] = False,
    consent: Annotated[
        RequestedCorrectionConsent | None,
        typer.Option(
            "--consent",
            help="API consent: reject, once, or persist for this exact local scope.",
        ),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
) -> None:
    """Generate a non-final review candidate through an explicitly consented API."""

    try:
        overrides: dict[str, object] = {"provider": provider_name.value}
        if model is not None:
            overrides["model"] = model
        if endpoint is not None:
            endpoint_key = (
                "openrouter_endpoint"
                if provider_name is RequestedCorrectionProvider.OPENROUTER
                else "endpoint"
            )
            overrides[endpoint_key] = endpoint
        if allow_remote_endpoint:
            overrides["allow_remote_endpoint"] = True
        if output_mode is not None:
            overrides["output_mode"] = output_mode
        if api_key_env is not None:
            overrides["openrouter_api_key_env"] = api_key_env
        if reasoning_max_tokens is not None:
            overrides["openrouter_reasoning_max_tokens"] = reasoning_max_tokens
        general_overrides: dict[str, object] = {}
        if allow_cloud:
            general_overrides["offline"] = False
        config = load_config(
            explicit_path=config_path,
            cli_overrides={"correction": overrides, "general": general_overrides},
        )
        provider = create_correction_provider(config)
        choice = _correction_consent_choice(config, provider, consent)
        typer.echo(
            "WARNING: Automated correction creates a review candidate, not a final "
            "transcript. Manually verify wording, speakers, punctuation, and quotation "
            "marks before acceptance.",
            err=True,
        )
        normalized_result = normalize_input_path(results_json)
        state_directory = _optional_user_path(resume_directory) or (
            normalized_result.parent / "correction-state-ewp-transcripts"
        )
        if preview:
            outcome = preview_correction(
                normalized_result,
                config=config,
                provider=provider,
                source_revision_path=_optional_user_path(source_revision),
                consent_choice=choice,
                resume_directory=state_directory,
            )
            typer.echo(f"PREVIEW {outcome.base_result_path}")
            typer.echo(
                "SUMMARY published=0 "
                f"revision_tokens={outcome.revision.statistics.revision_tokens} "
                f"warnings={len(outcome.revision.warnings)}"
            )
            return
        applied = apply_correction(
            normalized_result,
            config=config,
            provider=provider,
            source_revision_path=_optional_user_path(source_revision),
            consent_choice=choice,
            output_directory=_optional_user_path(output_directory),
            resume_directory=state_directory,
        )
    except ApplicationError as error:
        _expected_error(error)
    typer.echo(f"APPLIED {applied.base_result_path}")
    typer.echo(f"  REVISION {applied.revision_path}")
    typer.echo(
        f"SUMMARY revision_number={applied.revision.revision_number} "
        f"revision_tokens={applied.revision.statistics.revision_tokens} "
        f"warnings={len(applied.revision.warnings)}"
    )


def _correction_consent_choice(
    config: ApplicationConfig,
    provider: CorrectionProvider,
    requested: RequestedCorrectionConsent | None,
) -> ConsentChoice | None:
    """Display the API warning and obtain consent only when exact stored scope is absent."""

    # Kept behind the CLI adapter; application services independently enforce the scope.
    scope = CorrectionConsentScope(
        provider_id=provider.provider_id,
        endpoint_kind=provider.endpoint_kind,
        endpoint_identity=provider.endpoint_identity,
    )
    warning = correction_api_warning(scope.endpoint_kind)
    if warning is not None:
        typer.echo(f"WARNING: {warning}", err=True)
    if scope.endpoint_kind == "local" and not is_loopback_endpoint(scope.endpoint_identity):
        typer.echo(f"WARNING: {REMOTE_LOCAL_API_WARNING}", err=True)
    records = load_correction_consents(config.correction.consent_store)
    if any(record.scope == scope for record in records):
        return None
    if requested is not None:
        return _consent_value(requested)
    if not config.general.interactive:
        return None
    answer = typer.prompt("Consent [reject/once/persist]", default="reject").strip().casefold()
    try:
        selected = RequestedCorrectionConsent(answer)
    except ValueError as error:
        raise typer.BadParameter("consent must be reject, once, or persist") from error
    return _consent_value(selected)


def _consent_value(requested: RequestedCorrectionConsent) -> ConsentChoice:
    if requested is RequestedCorrectionConsent.REJECT:
        return "reject"
    if requested is RequestedCorrectionConsent.ONCE:
        return "accept_once"
    return "accept_persistently"


@revise_app.command("audit")
def revise_audit_command(
    revision_path: Annotated[
        Path,
        typer.Argument(help="Immutable transcript revision JSON.", metavar="REVISION"),
    ],
    results_directory: Annotated[
        Path | None,
        typer.Option("--results-dir", help="Directory containing the exact base result."),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write the audit JSON to this directory."),
    ] = None,
    no_write: Annotated[
        bool,
        typer.Option("--no-write", help="Reconstruct and display without publishing an audit."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the reconstructed audit to stdout as JSON."),
    ] = False,
) -> None:
    """Reconstruct detailed diagnostics from a base result and full revision."""

    try:
        config = load_config(explicit_path=config_path)
        outcome = audit_revision_file(
            revision_path,
            config=config,
            results_directory=_optional_user_path(results_directory),
            output_directory=_optional_user_path(output_directory),
            publish=not no_write,
        )
    except ApplicationError as error:
        _expected_error(error)
    if json_output:
        typer.echo(json.dumps(outcome.audit, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"AUDIT {outcome.revision_path}")
        if outcome.audit_path is not None:
            typer.echo(f"  WROTE {outcome.audit_path}")
        changes = outcome.audit.get("changes")
        change_count = len(changes) if isinstance(changes, list) else 0
        typer.echo(f"SUMMARY changes={change_count} written={int(outcome.audit_path is not None)}")


@revise_app.command("edit")
def revise_edit_command(
    results_json: Annotated[
        Path,
        typer.Argument(help="Completed canonical result to review.", metavar="RESULTS_JSON"),
    ],
    review_output_directory: Annotated[
        Path | None,
        typer.Option(
            "--review-output-dir",
            help="Write the editable EWP-REVIEW file to this directory.",
        ),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write the immutable revision to this directory."),
    ] = None,
    no_apply: Annotated[
        bool,
        typer.Option(
            "--no-apply",
            help="Keep editor changes without automatically creating a revision.",
        ),
    ] = False,
    audit: Annotated[
        bool,
        typer.Option("--audit", help="Publish detailed diagnostics after automatic apply."),
    ] = False,
    editor: Annotated[
        str | None,
        typer.Option(
            "--editor",
            help="Installed editor command, for example 'nano' or 'code --wait'.",
        ),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
) -> None:
    """Edit a prepared review; successful editor close applies it unless --no-apply."""

    try:
        normalized_result = normalize_input_path(results_json)
        config = load_config(
            explicit_path=config_path,
            cli_overrides=({"revision": {"editor": editor}} if editor is not None else None),
        )
        review_directory = _optional_user_path(review_output_directory) or (
            normalized_result.parent / "review-ewp-transcripts"
        )
        prepared = prepare_review_file(
            normalized_result,
            output_directory=review_directory,
            anchor_target_words=config.revision.anchor_target_words,
            lock_timeout_seconds=config.runtime.lock_timeout_seconds,
        )
        original_review = prepared.path.read_bytes()
        open_review_in_editor(prepared.path, configured=config.revision.editor)
        require_review_change(prepared.path, original_content=original_review)
        if no_apply:
            typer.echo(f"EDITED {prepared.path}")
            typer.echo("SUMMARY applied=0")
            return
        applied = apply_review_file(
            prepared.path,
            config=config,
            results_directory=normalized_result.parent,
            output_directory=_optional_user_path(output_directory),
        )
        audit_path = None
        if audit or config.revision.generate_audit:
            audit_path = audit_revision_file(
                applied.revision_path,
                config=config,
                results_directory=normalized_result.parent,
                output_directory=_optional_user_path(output_directory),
            ).audit_path
    except ApplicationError as error:
        _expected_error(error)
    typer.echo(f"EDITED {prepared.path}")
    typer.echo(f"APPLIED {applied.revision_path}")
    if audit_path is not None:
        typer.echo(f"AUDIT {audit_path}")
    typer.echo(f"SUMMARY applied=1 revision_number={applied.revision.revision_number}")


@app.command("doctor")
def doctor_command(
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the diagnostic result as JSON."),
    ] = False,
) -> None:
    """Check the local environment without loading transcription models."""

    try:
        config = load_config(explicit_path=config_path)
        result = doctor(config=config)
    except ApplicationError as error:
        _expected_error(error)
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
    else:
        for check in result.checks:
            typer.echo(f"{check.code}: {check.status.value.upper()} — {check.message}")

    if not result.ready:
        raise typer.Exit(code=3)


def _speaker_count(value: str | None) -> str | int | None:
    if value is None or value == "auto":
        return value
    try:
        parsed = int(value)
    except ValueError as error:
        raise typer.BadParameter("must be 'auto' or a positive integer") from error
    if parsed < 1:
        raise typer.BadParameter("must be 'auto' or a positive integer")
    return parsed


def _speaker_mapping(values: list[str] | None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for value in values or []:
        source, separator, label = value.partition("=")
        source = source.strip()
        label = label.strip()
        if not separator or not source or not label:
            raise typer.BadParameter("speaker maps must use SOURCE=NAME")
        if source in mapping:
            raise typer.BadParameter(f"speaker map source repeated: {source}")
        mapping[source] = label
    return mapping


def _inspection_overrides(
    *,
    recursive: bool | None,
    language: RequestedLanguage | None,
    channel_mode: RequestedChannelMode | None,
    speaker_count: str | int | None,
) -> dict[str, object]:
    overrides: dict[str, object] = {}
    if language is not None:
        overrides["general"] = {"language": LanguageMode(language.value)}
    if recursive is not None:
        overrides["input"] = {"recursive": recursive}
    if channel_mode is not None:
        overrides["channels"] = {"mode": ChannelMode(channel_mode.value)}
    if speaker_count is not None:
        overrides["diarization"] = {"speaker_count": speaker_count}
    return overrides


def _transcribe_overrides(
    *,
    recursive: bool,
    language: RequestedLanguage | None,
    channel_mode: RequestedChannelMode | None,
    speaker_count: str | int | None,
    preset: RequestedPreset,
    formats: list[RequestedTranscribeFormat] | None,
    segments: bool,
    keep_temp: bool,
    non_interactive: bool,
) -> dict[str, object]:
    overrides = _inspection_overrides(
        recursive=recursive,
        language=language,
        channel_mode=channel_mode,
        speaker_count=speaker_count,
    )
    general: dict[str, object] = {"preset": preset.value}
    if language is not None:
        general["language"] = LanguageMode(language.value)
    if non_interactive:
        general["interactive"] = False
    overrides["general"] = general
    if formats is not None:
        selected = {format_.value for format_ in formats or []}
        overrides["outputs"] = {
            "generate_txt": "txt" in selected,
            "generate_srt": "srt" in selected,
            "generate_vtt": "vtt" in selected,
            "generate_segments_json": segments,
        }
    elif segments:
        overrides["outputs"] = {"generate_segments_json": True}
    if keep_temp:
        overrides["runtime"] = {"keep_temp_on_success": True}
    return overrides


def _expected_error(error: ApplicationError) -> None:
    typer.echo(f"Error: {error}", err=True)
    if isinstance(error, InvalidConfigurationError):
        raise typer.Exit(code=2) from error
    if isinstance(error, MissingCapabilityError):
        raise typer.Exit(code=3) from error
    if isinstance(error, (OutputLockUnavailableError, OutputReservationError)):
        raise typer.Exit(code=7) from error
    if isinstance(error, InvalidCanonicalResultError):
        raise typer.Exit(code=8) from error
    raise typer.Exit(code=4) from error


def _input_selection(
    input_path: Path | None,
    group_paths: list[Path] | None,
    group_id: str | None,
) -> tuple[Path, tuple[Path, ...] | None, str | None]:
    explicit = tuple(normalize_input_path(path) for path in group_paths or ())
    if explicit:
        if input_path is not None:
            raise typer.BadParameter("INPUT cannot be combined with --group")
        if len(explicit) < 2:
            raise typer.BadParameter("--group must be repeated for at least two files")
        if group_id is None or not group_id.strip():
            raise typer.BadParameter("--group-id is required with --group")
        return explicit[0], explicit, group_id.strip()
    if group_id is not None:
        raise typer.BadParameter("--group-id requires --group")
    if input_path is None:
        raise typer.BadParameter("provide INPUT or an explicit --group")
    return normalize_input_path(input_path), None, None


def _optional_user_path(path: Path | None) -> Path | None:
    """Normalize an optional Windows, WSL, POSIX, or relative CLI path."""

    return normalize_input_path(path) if path is not None else None


@app.command("clean")
def clean_command(
    target: Annotated[
        CleanTarget,
        typer.Argument(help="Cleanup scope; the MVP supports only all-workdirs."),
    ],
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="List eligible workspaces without removing them."),
    ] = False,
    confirmed: Annotated[
        bool,
        typer.Option("--yes", help="Confirm removal of every listed eligible workspace."),
    ] = False,
    older_than_days: Annotated[
        int,
        typer.Option(
            "--older-than",
            min=0,
            help="Select workspaces at least this many days old.",
        ),
    ] = 0,
) -> None:
    """Safely preview or remove marker-verified application workspaces."""

    if dry_run == confirmed:
        raise typer.BadParameter("choose exactly one of --dry-run or --yes")
    assert target is CleanTarget.ALL_WORKDIRS
    try:
        config = load_config(explicit_path=config_path)
        outcome = clean_all_workdirs(
            config=config,
            older_than_days=older_than_days,
            dry_run=dry_run,
        )
    except ApplicationError as error:
        _expected_error(error)
    action = "WOULD REMOVE" if outcome.dry_run else "REMOVED"
    for path in outcome.paths:
        typer.echo(f"{action} {path}")
    typer.echo(
        f"SUMMARY selected={len(outcome.paths)} removed="
        f"{0 if outcome.dry_run else len(outcome.paths)}"
    )


@app.command("inspect")
def inspect_command(
    input_path: Annotated[
        Path | None,
        typer.Argument(help="Audio file or directory to inspect.", metavar="INPUT"),
    ] = None,
    group_paths: Annotated[
        list[Path] | None,
        typer.Option("--group", help="Explicit source file; repeat for each group member."),
    ] = None,
    group_id: Annotated[
        str | None,
        typer.Option("--group-id", help="Collision-safe output identity for an explicit group."),
    ] = None,
    recursive: Annotated[
        bool | None,
        typer.Option("--recursive", help="Inspect supported files in subdirectories."),
    ] = None,
    language: Annotated[
        RequestedLanguage | None,
        typer.Option("--language", help="Transcription language: pl, en, or auto."),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    channel_mode: Annotated[
        RequestedChannelMode | None,
        typer.Option("--channel-mode", help="Override automatic channel classification."),
    ] = None,
    speaker_count: Annotated[
        str | None,
        typer.Option("--speaker-count", help="Expected speakers: 'auto' or a positive integer."),
    ] = None,
    allow_duration_mismatch: Annotated[
        bool,
        typer.Option(
            "--allow-duration-mismatch",
            help="Allow grouped-source duration differences above the error threshold.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the complete inspection result as JSON."),
    ] = False,
) -> None:
    """Inspect and classify audio without loading transcription models."""

    try:
        selected_input, explicit_group_paths, explicit_group_id = _input_selection(
            input_path, group_paths, group_id
        )
        parsed_speaker_count = _speaker_count(speaker_count)
        config = load_config(
            explicit_path=config_path,
            cli_overrides=_inspection_overrides(
                recursive=recursive,
                language=language,
                channel_mode=channel_mode,
                speaker_count=parsed_speaker_count,
            ),
        )
        result = inspect_input(
            selected_input,
            config=config,
            allow_duration_mismatch=allow_duration_mismatch,
            explicit_group_paths=explicit_group_paths,
            explicit_group_id=explicit_group_id,
        )
    except ApplicationError as error:
        _expected_error(error)

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"Input: {result.discovery.input_path}")
    typer.echo(f"Episodes: {len(result.episodes)}")
    typer.echo(f"Skipped paths: {len(result.discovery.skipped)}")
    for episode in result.episodes:
        typer.echo(
            f"\n{episode.job_id}: {episode.duration_ms} ms, {len(episode.sources)} source(s)"
        )
        for source in episode.sources:
            classification = source.channel_classification
            typer.echo(
                f"  {source.fingerprint.filename}: {source.stream.channels} channel(s), "
                f"detected={classification.detected_mode.value}, "
                f"processing={classification.processing_mode.value}"
            )
        for warning in episode.warnings:
            typer.echo(f"  WARNING {warning.code.value}: {warning.message}")


def _planned_paths(job: JobOutputPlan) -> tuple[Path, ...]:
    if job.outputs is None:
        return ()
    return tuple(
        path
        for path in (
            job.outputs.results,
            job.outputs.transcript,
            job.outputs.subtitles_srt,
            job.outputs.subtitles_vtt,
            job.outputs.segments,
        )
        if path is not None
    )


@app.command("dry-run")
def dry_run_command(
    input_path: Annotated[
        Path | None,
        typer.Argument(help="Audio file or directory to plan.", metavar="INPUT"),
    ] = None,
    group_paths: Annotated[
        list[Path] | None,
        typer.Option("--group", help="Explicit source file; repeat for each group member."),
    ] = None,
    group_id: Annotated[
        str | None,
        typer.Option("--group-id", help="Collision-safe output identity for an explicit group."),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Plan final outputs in this directory."),
    ] = None,
    recursive: Annotated[
        bool | None,
        typer.Option("--recursive", help="Inspect supported files in subdirectories."),
    ] = None,
    language: Annotated[
        RequestedLanguage | None,
        typer.Option("--language", help="Transcription language: pl, en, or auto."),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    channel_mode: Annotated[
        RequestedChannelMode | None,
        typer.Option("--channel-mode", help="Override automatic channel classification."),
    ] = None,
    speaker_count: Annotated[
        str | None,
        typer.Option(
            "--speaker-count",
            help="Use one speaker, an exact positive count, or 'auto'.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Plan a new result version even for a duplicate."),
    ] = False,
    allow_duration_mismatch: Annotated[
        bool,
        typer.Option(
            "--allow-duration-mismatch",
            help="Allow grouped-source duration differences above the error threshold.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the complete execution plan as JSON."),
    ] = False,
) -> None:
    """Plan a run without creating outputs, workdirs, or loading models."""

    try:
        selected_input, explicit_group_paths, explicit_group_id = _input_selection(
            input_path, group_paths, group_id
        )
        parsed_speaker_count = _speaker_count(speaker_count)
        config = load_config(
            explicit_path=config_path,
            cli_overrides=_inspection_overrides(
                recursive=recursive,
                language=language,
                channel_mode=channel_mode,
                speaker_count=parsed_speaker_count,
            ),
        )
        result = dry_run(
            selected_input,
            config=config,
            output_directory=_optional_user_path(output_directory),
            force=force,
            allow_duration_mismatch=allow_duration_mismatch,
            explicit_group_paths=explicit_group_paths,
            explicit_group_id=explicit_group_id,
        )
    except ApplicationError as error:
        _expected_error(error)

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"Output directory: {result.output_directory}")
    episodes = {episode.job_id: episode for episode in result.inspection.episodes}
    for job in result.jobs:
        episode = episodes[job.job_id]
        typer.echo(f"\n{job.decision.value.upper()} {job.job_id}")
        typer.echo(f"  language: {result.language.value}")
        for source in episode.sources:
            speaker = source.speaker_label or source.speaker_id
            typer.echo(f"  source: {source.fingerprint.filename} ({speaker})")
            typer.echo(
                f"    channels: detected={source.channel_classification.detected_mode.value}, "
                f"processing={source.channel_classification.processing_mode.value}"
            )
        if job.outputs is not None:
            typer.echo(f"  result version: {job.outputs.result_version}")
            for path in _planned_paths(job):
                typer.echo(f"  output: {path}")
        elif job.existing_result is not None:
            typer.echo(f"  existing result: {job.existing_result.path}")
        for warning in (*episode.warnings, *job.warnings):
            typer.echo(f"  WARNING {warning.code.value}: {warning.message}")


@app.command("export")
def export_command(
    results_json: Annotated[
        Path,
        typer.Argument(
            help="Completed canonical result or directory containing results.",
            metavar="RESULTS_OR_DIRECTORY",
        ),
    ],
    formats: Annotated[
        list[ExportFormat] | None,
        typer.Option("--format", help="Export format; may be repeated."),
    ] = None,
    segments: Annotated[
        bool,
        typer.Option("--segments", help="Generate the optional segments JSON export."),
    ] = False,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write exports to this directory."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Create the first free later export version."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    subtitle_preset: Annotated[
        RequestedSubtitlePreset,
        typer.Option("--subtitle-preset", help="Subtitle readability preset."),
    ] = RequestedSubtitlePreset.YOUTUBE,
    speaker_labels: Annotated[
        RequestedSpeakerLabels | None,
        typer.Option("--speaker-labels", help="Subtitle speaker-label behavior."),
    ] = None,
    revision: Annotated[
        str,
        typer.Option(
            "--revision",
            help=(
                "Corrected transcript selection: none, latest, a revision JSON path, "
                "or a revision directory for batch export."
            ),
        ),
    ] = "none",
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Include canonical results in subdirectories."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Write the batch outcome as JSON."),
    ] = False,
) -> None:
    """Regenerate exports from canonical JSON without opening source audio."""

    try:
        config = load_config(explicit_path=config_path)
        subtitles_config = config.subtitles.model_copy(
            update={
                "preset": subtitle_preset.value,
                **({"speaker_labels": speaker_labels.value} if speaker_labels is not None else {}),
            }
        )
        requested = list(formats or [])
        if segments:
            requested.append(ExportFormat.SEGMENTS)
        if not requested:
            requested = [
                format_
                for enabled, format_ in (
                    (config.outputs.generate_txt, ExportFormat.TXT),
                    (config.outputs.generate_srt, ExportFormat.SRT),
                    (config.outputs.generate_vtt, ExportFormat.VTT),
                    (config.outputs.generate_segments_json, ExportFormat.SEGMENTS),
                )
                if enabled
            ]
        normalized_results = normalize_input_path(results_json)
        selected_revision: str | Path = revision
        if revision not in {"none", "latest"}:
            selected_revision = normalize_input_path(revision)
        if normalized_results.is_dir():
            if isinstance(selected_revision, Path) and not selected_revision.is_dir():
                raise InvalidCanonicalResultError(
                    "Directory export requires --revision none, latest, or a revision directory"
                )
            batch = export_batch(
                normalized_results,
                formats=tuple(requested),
                output_directory=_optional_user_path(output_directory),
                force=force,
                subtitles_config=subtitles_config,
                revision=selected_revision,
                recursive=recursive,
                continue_after_error=config.runtime.continue_batch_after_error,
            )
        else:
            outcome = export_result(
                normalized_results,
                formats=tuple(requested),
                output_directory=_optional_user_path(output_directory),
                force=force,
                subtitles_config=subtitles_config,
                revision=selected_revision,
            )
    except ApplicationError as error:
        _expected_error(error)

    if normalized_results.is_dir():
        if json_output:
            typer.echo(_export_batch_json(batch))
        else:
            _print_export_batch(batch)
        if batch.failed:
            raise typer.Exit(code=5)
        return

    typer.echo(f"Export version: {outcome.result_version}")
    if outcome.revision_number is not None:
        typer.echo(f"Revision number: {outcome.revision_number}")
    for path in outcome.written:
        typer.echo(f"WROTE {path}")
    for path in outcome.skipped:
        typer.echo(f"SKIP {path}")


@app.command("transcribe")
def transcribe_command(
    input_path: Annotated[
        Path | None,
        typer.Argument(help="Audio file or directory to transcribe.", metavar="INPUT"),
    ] = None,
    group_paths: Annotated[
        list[Path] | None,
        typer.Option("--group", help="Explicit source file; repeat for each group member."),
    ] = None,
    group_id: Annotated[
        str | None,
        typer.Option("--group-id", help="Collision-safe output identity for an explicit group."),
    ] = None,
    output_directory: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write results and exports to this directory."),
    ] = None,
    recursive: Annotated[
        bool | None,
        typer.Option("--recursive", help="Include supported files in subdirectories."),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Read an explicit TOML configuration file."),
    ] = None,
    language: Annotated[
        RequestedLanguage | None,
        typer.Option("--language", help="Transcription language: pl, en, or auto."),
    ] = None,
    channel_mode: Annotated[
        RequestedChannelMode | None,
        typer.Option("--channel-mode", help="Override automatic channel classification."),
    ] = None,
    speaker_count: Annotated[
        str | None,
        typer.Option(
            "--speaker-count",
            help="Use one speaker, an exact positive count, or 'auto'.",
        ),
    ] = None,
    speaker: Annotated[
        str | None,
        typer.Option("--speaker", help="Explicit label for one single-speaker source."),
    ] = None,
    speaker_maps: Annotated[
        list[str] | None,
        typer.Option(
            "--speaker-map",
            help="Explicit SOURCE=NAME label; SOURCE is an exact filename; may be repeated.",
        ),
    ] = None,
    preset: Annotated[
        RequestedPreset,
        typer.Option("--preset", help="Select the transcription preset."),
    ] = RequestedPreset.ACCURATE,
    formats: Annotated[
        list[RequestedTranscribeFormat] | None,
        typer.Option("--format", help="Generated text format; may be repeated."),
    ] = None,
    segments: Annotated[
        bool,
        typer.Option("--segments", help="Generate the optional segments JSON export."),
    ] = False,
    keep_temp: Annotated[
        bool,
        typer.Option("--keep-temp", help="Retain the owned workspace after success."),
    ] = False,
    non_interactive: Annotated[
        bool,
        typer.Option("--non-interactive", help="Disable all interactive behavior."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Create a new result version for a duplicate input."),
    ] = False,
    allow_duration_mismatch: Annotated[
        bool,
        typer.Option(
            "--allow-duration-mismatch",
            help="Allow grouped-source duration differences above the error threshold.",
        ),
    ] = False,
) -> None:
    """Transcribe audio with pinned local models."""

    config = None
    try:
        selected_input, explicit_group_paths, explicit_group_id = _input_selection(
            input_path, group_paths, group_id
        )
        parsed_speaker_count = _speaker_count(speaker_count)
        parsed_speaker_map = _speaker_mapping(speaker_maps)
        if speaker is not None and not speaker.strip():
            raise typer.BadParameter("speaker label must not be empty")
        if speaker is not None and (selected_input.is_dir() or explicit_group_paths is not None):
            raise typer.BadParameter("--speaker requires one input file")
        if speaker is not None and parsed_speaker_count not in {None, 1}:
            raise typer.BadParameter("--speaker requires --speaker-count 1")
        config = load_config(
            explicit_path=config_path,
            cli_overrides=_transcribe_overrides(
                recursive=bool(recursive) if selected_input.is_dir() else False,
                language=language,
                channel_mode=channel_mode,
                speaker_count=1 if speaker is not None else parsed_speaker_count,
                preset=preset,
                formats=formats,
                segments=segments,
                keep_temp=keep_temp,
                non_interactive=non_interactive,
            ),
        )
        output_guard = (
            redirect_stdout(sys.stderr) if config.runtime.log_format == "jsonl" else nullcontext()
        )
        with output_guard:
            if selected_input.is_dir() and explicit_group_paths is None:
                batch = transcribe_batch(
                    selected_input,
                    config=config,
                    output_directory=_optional_user_path(output_directory),
                    force=force,
                    allow_duration_mismatch=allow_duration_mismatch,
                    speaker_map=parsed_speaker_map,
                )
            else:
                outcome = transcribe_one(
                    selected_input,
                    config=config,
                    output_directory=_optional_user_path(output_directory),
                    force=force,
                    allow_duration_mismatch=allow_duration_mismatch,
                    speaker_label=speaker.strip() if speaker is not None else None,
                    speaker_map=parsed_speaker_map,
                    explicit_group_paths=explicit_group_paths,
                    explicit_group_id=explicit_group_id,
                )
    except ApplicationError as error:
        if config is not None and config.runtime.log_format == "jsonl":
            _emit_jsonl(
                level="error",
                event="TRANSCRIPTION_FAILED",
                run_id=None,
                job_id=None,
                stage="complete",
                elapsed_ms=None,
                context={
                    "error_type": type(error).__name__,
                    "message": str(error),
                },
            )
        _expected_error(error)

    assert config is not None
    if selected_input.is_dir() and explicit_group_paths is None:
        _print_batch_outcome(batch, log_format=config.runtime.log_format)
    else:
        _print_transcription_outcome(outcome, log_format=config.runtime.log_format)


def _print_transcription_outcome(
    outcome: TranscriptionOutcome, *, log_format: str = "text"
) -> None:
    if log_format == "jsonl":
        _emit_jsonl(
            level="info",
            event="TRANSCRIPTION_COMPLETED"
            if outcome.decision is PlanDecision.PROCESS
            else "TRANSCRIPTION_SKIPPED",
            run_id=outcome.run_id,
            job_id=outcome.job_id,
            stage="complete",
            elapsed_ms=outcome.elapsed_ms,
            context={
                "decision": outcome.decision.value,
                "result_path": str(outcome.result_path),
                "exports_written": [str(path) for path in outcome.exports.written]
                if outcome.exports is not None
                else [],
                "exports_skipped": [str(path) for path in outcome.exports.skipped]
                if outcome.exports is not None
                else [],
            },
        )
        return
    typer.echo(f"{outcome.decision.value.upper()} {outcome.job_id}")
    typer.echo(f"RESULT {outcome.result_path}")
    if outcome.exports is not None:
        for path in outcome.exports.written:
            typer.echo(f"WROTE {path}")
        for path in outcome.exports.skipped:
            typer.echo(f"SKIP {path}")


def _print_batch_outcome(outcome: BatchTranscriptionOutcome, *, log_format: str = "text") -> None:
    if log_format == "jsonl":
        for job in outcome.jobs:
            _emit_jsonl(
                level="error" if job.status == "failed" else "info",
                event=f"JOB_{job.status.upper()}",
                run_id=job.run_id,
                job_id=job.job_id,
                stage="complete",
                elapsed_ms=job.elapsed_ms,
                context={
                    "result_path": str(job.result_path) if job.result_path is not None else None,
                    "failure_code": job.failure_code,
                    "failure_message": job.failure_message,
                },
            )
        _emit_jsonl(
            level="error" if outcome.failed else "info",
            event="BATCH_SUMMARY",
            run_id=None,
            job_id=None,
            stage="complete",
            elapsed_ms=sum(job.elapsed_ms or 0 for job in outcome.jobs),
            context={
                "output_directory": str(outcome.output_directory),
                "completed": outcome.completed,
                "skipped": outcome.skipped,
                "failed": outcome.failed,
                "cancelled": outcome.cancelled,
            },
        )
        if outcome.cancelled:
            raise typer.Exit(code=6)
        if outcome.failed:
            raise typer.Exit(code=5)
        return
    typer.echo(f"Output directory: {outcome.output_directory}")
    for job in outcome.jobs:
        typer.echo(f"{job.status.upper()} {job.job_id}")
        if job.result_path is not None:
            typer.echo(f"  RESULT {job.result_path}")
        if job.failure_code is not None:
            typer.echo(f"  ERROR {job.failure_code}: {job.failure_message}")
    typer.echo(
        f"SUMMARY completed={outcome.completed} skipped={outcome.skipped} "
        f"failed={outcome.failed} cancelled={outcome.cancelled}"
    )
    if outcome.cancelled:
        raise typer.Exit(code=6)
    if outcome.failed:
        raise typer.Exit(code=5)


def _emit_jsonl(
    *,
    level: str,
    event: str,
    run_id: object,
    job_id: str | None,
    stage: str,
    elapsed_ms: int | None,
    context: dict[str, object],
) -> None:
    typer.echo(
        json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": level,
                "event": event,
                "run_id": str(run_id) if run_id is not None else None,
                "job_id": job_id,
                "source": None,
                "stage": stage,
                "elapsed_ms": elapsed_ms,
                "context": context,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


def main() -> None:
    """Run the command-line adapter."""

    app()
