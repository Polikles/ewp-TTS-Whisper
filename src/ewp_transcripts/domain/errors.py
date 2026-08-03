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


class OutputLockUnavailableError(ApplicationError):
    """Raised when an output directory cannot be locked within the configured timeout."""


class OutputReservationError(ApplicationError):
    """Raised when a planned running-state filename cannot be reserved safely."""


class InvalidJobStateError(ApplicationError):
    """Raised when a persisted job state cannot be trusted or transitioned."""
