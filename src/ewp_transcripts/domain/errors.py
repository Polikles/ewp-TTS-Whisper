"""Controlled errors exposed by the application layer."""


class ApplicationError(Exception):
    """Base class for expected EWP-transcripts failures."""


class MissingCapabilityError(ApplicationError):
    """Raised when the environment lacks a required runtime capability."""
