"""Controlled errors exposed by the application layer."""


class ApplicationError(Exception):
    """Base class for expected EWP-transcripts failures."""

    code = "APPLICATION_ERROR"


class MissingCapabilityError(ApplicationError):
    """Raised when the environment lacks a required runtime capability."""

    code = "MISSING_CAPABILITY"


class InvalidConfigurationError(ApplicationError):
    """Raised when a configuration source cannot be read or validated."""

    code = "INVALID_CONFIGURATION"


class InputNotFoundError(ApplicationError):
    """Raised when the supplied input path does not exist."""

    code = "INPUT_NOT_FOUND"


class UnsupportedInputError(ApplicationError):
    """Raised when the supplied input is neither a regular file nor directory."""

    code = "UNSUPPORTED_INPUT"


class SymlinkInputError(ApplicationError):
    """Raised when a symbolic link is supplied as the direct input."""

    code = "SYMLINK_INPUT"


class MediaProbeError(ApplicationError):
    """Raised when ffprobe cannot inspect or normalize an input."""

    code = "MEDIA_PROBE_FAILED"


class AudioPreparationError(ApplicationError):
    """Raised when FFmpeg cannot create a safe working-audio file."""

    code = "AUDIO_PREPARATION_FAILED"


class TranscriptNormalizationError(ApplicationError):
    """Raised when engine timing cannot form a valid canonical timeline."""

    code = "TRANSCRIPT_NORMALIZATION_FAILED"


class UnsupportedPipelineScopeError(ApplicationError):
    """Raised when a job is outside the currently implemented pipeline slice."""

    code = "UNSUPPORTED_PIPELINE_SCOPE"


class SpeechEngineError(ApplicationError):
    """Raised when a speech backend cannot load or return valid normalized output."""

    code = "SPEECH_ENGINE_ERROR"


class NoAudioStreamError(MediaProbeError):
    """Raised when an inspected input contains no supported audio stream."""

    code = "NO_AUDIO_STREAM"


class AmbiguousGroupError(ApplicationError):
    """Raised when filename conventions cannot produce a unique episode group."""

    code = "AMBIGUOUS_GROUP"


class MultipleAudioStreamsError(ApplicationError):
    """Raised when an input has multiple audio streams and none was selected."""

    code = "MULTIPLE_AUDIO_STREAMS"


class SampleRateMismatchError(ApplicationError):
    """Raised when grouped sources do not share a sample rate."""

    code = "SAMPLE_RATE_MISMATCH"


class DurationMismatchError(ApplicationError):
    """Raised when grouped-source duration drift exceeds the allowed threshold."""

    code = "DURATION_MISMATCH"


class ChannelAnalysisError(ApplicationError):
    """Raised when FFmpeg cannot provide valid channel-analysis samples."""

    code = "CHANNEL_ANALYSIS_FAILED"


class UnsafeOutputNameError(ApplicationError):
    """Raised when a job identifier cannot safely become one output filename."""

    code = "UNSAFE_OUTPUT_NAME"


class InvalidExistingResultError(ApplicationError):
    """Raised when completed-result metadata is unreadable or inconsistent."""

    code = "INVALID_EXISTING_RESULT"


class InvalidCanonicalResultError(ApplicationError):
    """Raised when a canonical result cannot be safely read or exported."""

    code = "INVALID_CANONICAL_RESULT"


class InvalidRevisionError(ApplicationError):
    """Raised when a transcript revision is invalid or incompatible with its base."""

    code = "INVALID_REVISION"


class InvalidTranslationError(ApplicationError):
    """Raised when a translation artifact is invalid or incompatible with its source."""

    code = "INVALID_TRANSLATION"


class InvalidTranslationResponseError(InvalidTranslationError):
    """Raised when an automated-translation response violates its request contract."""

    code = "INVALID_TRANSLATION_RESPONSE"


class TranslationProviderError(ApplicationError):
    """Base class for sanitized automated-translation provider failures."""

    code = "TRANSLATION_PROVIDER_ERROR"


class TranslationProviderUnavailableError(TranslationProviderError):
    """Raised when the selected translation endpoint cannot serve requests."""

    code = "TRANSLATION_PROVIDER_UNAVAILABLE"


class TranslationModelUnavailableError(TranslationProviderError):
    """Raised when the selected endpoint does not advertise the requested model."""

    code = "TRANSLATION_MODEL_UNAVAILABLE"


class RetryableTranslationProviderError(TranslationProviderError):
    """Raised for an explicitly retryable translation-provider failure."""

    code = "TRANSLATION_PROVIDER_RETRYABLE"


class PermanentTranslationProviderError(TranslationProviderError):
    """Raised for a translation-provider failure that must not be retried."""

    code = "TRANSLATION_PROVIDER_PERMANENT"


class PermanentTranslationHttpError(PermanentTranslationProviderError):
    """Content-free permanent HTTP rejection with a safe numeric status."""

    code = "TRANSLATION_PROVIDER_HTTP_REJECTED"

    def __init__(self, status_code: int) -> None:
        super().__init__("Translation provider HTTP request was rejected")
        self.status_code = status_code


class InvalidCorrectionResponseError(ApplicationError):
    """Raised when provider output cannot be trusted as a correction proposal."""

    code = "INVALID_CORRECTION_RESPONSE"


class CorrectionProviderError(ApplicationError):
    """Base class for sanitized correction-provider failures."""

    code = "CORRECTION_PROVIDER_ERROR"


class RetryableCorrectionProviderError(CorrectionProviderError):
    """Raised for an explicitly retryable transport, rate-limit, or server failure."""

    code = "CORRECTION_PROVIDER_RETRYABLE"


class PermanentCorrectionProviderError(CorrectionProviderError):
    """Raised for a provider failure that must not be retried automatically."""

    code = "CORRECTION_PROVIDER_PERMANENT"


class CorrectionConsentError(ApplicationError):
    """Raised when an external correction API boundary is not authorized."""

    code = "CORRECTION_CONSENT_REQUIRED"


class InvalidReviewError(InvalidRevisionError):
    """Raised with a stable code when an ``EWP-REVIEW`` file cannot be trusted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class RevisionEditorError(ApplicationError):
    """Raised when the external transcript-review editor cannot complete successfully."""

    code = "REVISION_EDITOR_FAILED"


class OutputLockUnavailableError(ApplicationError):
    """Raised when an output directory cannot be locked within the configured timeout."""

    code = "OUTPUT_LOCK_UNAVAILABLE"


class OutputReservationError(ApplicationError):
    """Raised when a planned running-state filename cannot be reserved safely."""

    code = "OUTPUT_RESERVATION_FAILED"


class InvalidJobStateError(ApplicationError):
    """Raised when a persisted job state cannot be trusted or transitioned."""

    code = "INVALID_JOB_STATE"


class UnsafeWorkDirectoryError(ApplicationError):
    """Raised when a work directory cannot be allocated or cleaned safely."""

    code = "UNSAFE_WORK_DIRECTORY"
