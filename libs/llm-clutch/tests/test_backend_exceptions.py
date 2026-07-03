"""Unit tests for the backend exception hierarchy."""

import pytest

from llm_clutch.backend.exceptions import (
    BackendError,
    InsufficientMemoryError,
    ModelLoadError,
    ModelUnloadError,
)


class TestBackendExceptions:
    """Tests for backend exception hierarchy."""

    def test_backend_error_is_an_exception(self) -> None:
        """Test that BackendError is an Exception."""
        assert issubclass(BackendError, Exception)

    def test_model_load_error_inherits_from_backend_error(self) -> None:
        """Test that ModelLoadError inherits from BackendError."""
        assert issubclass(ModelLoadError, BackendError)

    def test_model_unload_error_inherits_from_backend_error(self) -> None:
        """Test that ModelUnloadError inherits from BackendError."""
        assert issubclass(ModelUnloadError, BackendError)

    def test_insufficient_memory_error_inherits_from_backend_error(self) -> None:
        """Test that InsufficientMemoryError inherits from BackendError."""
        assert issubclass(InsufficientMemoryError, BackendError)

    def test_can_catch_all_backend_errors_with_base_exception(self) -> None:
        """Test that all backend errors can be caught with BackendError."""
        errors = [
            ModelLoadError("test"),
            ModelUnloadError("test"),
            InsufficientMemoryError("test"),
        ]

        for error in errors:
            try:
                raise error
            except BackendError:
                pass  # Successfully caught
            except Exception:
                error_name = error.__class__.__name__
                pytest.fail(f"Failed to catch {error_name} as BackendError")

    def test_model_load_error_can_be_raised_and_caught(self) -> None:
        """Test that ModelLoadError can be raised and caught."""
        with pytest.raises(ModelLoadError):
            raise ModelLoadError("Failed to load model")

    def test_model_unload_error_can_be_raised_and_caught(self) -> None:
        """Test that ModelUnloadError can be raised and caught."""
        with pytest.raises(ModelUnloadError):
            raise ModelUnloadError("Failed to unload model")

    def test_insufficient_memory_error_can_be_raised_and_caught(self) -> None:
        """Test that InsufficientMemoryError can be raised and caught."""
        with pytest.raises(InsufficientMemoryError):
            raise InsufficientMemoryError("Insufficient memory available")

    def test_exception_message_is_preserved(self) -> None:
        """Test that exception messages are preserved."""
        message = "Test error message"
        error = BackendError(message)
        assert str(error) == message
