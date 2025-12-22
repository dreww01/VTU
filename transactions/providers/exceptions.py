# transactions/providers/exceptions.py


class ProviderError(Exception):
    """Base exception for external provider issues."""


class VTPassError(ProviderError):
    """Raised when VTPass returns an error or unexpected response."""

    def __init__(self, message: str, payload: dict | None = None):
        self.payload = payload or {}
        super().__init__(message)
