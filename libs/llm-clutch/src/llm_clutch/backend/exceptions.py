"""Exception hierarchy for backend operations."""


class BackendError(Exception):
    """Base exception for all backend-related errors."""


class ModelLoadError(BackendError):
    """Exception raised when model loading fails."""


class ModelUnloadError(BackendError):
    """Exception raised when model unloading fails."""


class InsufficientMemoryError(BackendError):
    """Exception raised when there is insufficient memory to load a model."""
