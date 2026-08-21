"""Controlled errors exposed by the application layer."""


class ApplicationError(Exception):
    """Base class for expected EWP-transcripts failures."""


class MissingCapabilityError(ApplicationError):
    """Raised when the environment lacks a required runtime capability."""


class InvalidConfigurationError(ApplicationError):
    """Raised when a configuration source cannot be read or validated."""


class InputNotFoundError(ApplicationError):
    """Raised when the supplied input path does not exist."""


class UnsupportedInputError(ApplicationError):
    """Raised when the supplied input is neither a regular file nor directory."""


class SymlinkInputError(ApplicationError):
    """Raised when a symbolic link is supplied as the direct input."""


class MediaProbeError(ApplicationError):
    """Raised when ffprobe cannot inspect or normalize an input."""


class AudioPreparationError(ApplicationError):
    """Raised when FFmpeg cannot create a safe working-audio file."""


class TranscriptNormalizationError(ApplicationError):
    """Raised when engine timing cannot form a valid canonical timeline."""


class UnsupportedPipelineScopeError(ApplicationError):
    """Raised when a job is outside the currently implemented pipeline slice."""


class SpeechEngineError(ApplicationError):
    """Raised when a speech backend cannot load or return valid normalized output."""


class NoAudioStreamError(MediaProbeError):
    """Raised when an inspected input contains no supported audio stream."""


class AmbiguousGroupError(ApplicationError):
    """Raised when filename conventions cannot produce a unique episode group."""


class MultipleAudioStreamsError(ApplicationError):
    """Raised when an input has multiple audio streams and none was selected."""


class SampleRateMismatchError(ApplicationError):
    """Raised when grouped sources do not share a sample rate."""


class DurationMismatchError(ApplicationError):
    """Raised when grouped-source duration drift exceeds the allowed threshold."""


class ChannelAnalysisError(ApplicationError):
    """Raised when FFmpeg cannot provide valid channel-analysis samples."""


class UnsafeOutputNameError(ApplicationError):
    """Raised when a job identifier cannot safely become one output filename."""


class InvalidExistingResultError(ApplicationError):
    """Raised when completed-result metadata is unreadable or inconsistent."""


class InvalidCanonicalResultError(ApplicationError):
    """Raised when a canonical result cannot be safely read or exported."""


class InvalidRevisionError(ApplicationError):
    """Raised when a transcript revision is invalid or incompatible with its base."""


class InvalidTranslationError(ApplicationError):
    """Raised when a translation artifact is invalid or incompatible with its source."""


class InvalidCorrectionResponseError(ApplicationError):
    """Raised when provider output cannot be trusted as a correction proposal."""


class CorrectionProviderError(ApplicationError):
    """Base class for sanitized correction-provider failures."""


class RetryableCorrectionProviderError(CorrectionProviderError):
    """Raised for an explicitly retryable transport, rate-limit, or server failure."""


class PermanentCorrectionProviderError(CorrectionProviderError):
    """Raised for a provider failure that must not be retried automatically."""


class CorrectionConsentError(ApplicationError):
    """Raised when an external correction API boundary is not authorized."""


class InvalidReviewError(InvalidRevisionError):
    """Raised with a stable code when an ``EWP-REVIEW`` file cannot be trusted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class RevisionEditorError(ApplicationError):
    """Raised when the external transcript-review editor cannot complete successfully."""


class OutputLockUnavailableError(ApplicationError):
    """Raised when an output directory cannot be locked within the configured timeout."""


class OutputReservationError(ApplicationError):
    """Raised when a planned running-state filename cannot be reserved safely."""


class InvalidJobStateError(ApplicationError):
    """Raised when a persisted job state cannot be trusted or transitioned."""


class UnsafeWorkDirectoryError(ApplicationError):
    """Raised when a work directory cannot be allocated or cleaned safely."""
