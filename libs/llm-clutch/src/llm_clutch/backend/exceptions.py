"""Exception hierarchy for backend operations."""


class BackendError(Exception):
    """Base exception for all backend-related errors."""

    pass


class ModelLoadError(BackendError):
    """Exception raised when model loading fails."""

    pass


class ModelUnloadError(BackendError):
    """Exception raised when model unloading fails."""

    pass


class InsufficientMemoryError(BackendError):
    """Exception raised when there is insufficient memory to load a model."""

    pass
