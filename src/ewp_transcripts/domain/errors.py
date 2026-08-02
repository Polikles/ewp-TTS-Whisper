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
