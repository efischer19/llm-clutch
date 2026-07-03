"""Unit tests for the abstract ModelBackend class."""

import pytest

from llm_clutch.backend.base import ModelBackend


class TestModelBackendAbstraction:
    """Tests for ModelBackend abstract base class."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """Test that ModelBackend cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            ModelBackend()  # type: ignore

        assert "Can't instantiate abstract class" in str(exc_info.value)
        assert "ModelBackend" in str(exc_info.value)

    def test_concrete_subclass_missing_load_model_raises_type_error(self) -> None:
        """Test that a concrete subclass missing load_model raises TypeError."""

        class IncompleteBackend(ModelBackend):
            """Incomplete backend missing load_model."""

            async def unload_model(self) -> None:
                pass

            async def get_available_memory(self) -> int:
                return 0

            async def get_active_model(self) -> str | None:
                return None

        with pytest.raises(TypeError) as exc_info:
            IncompleteBackend()  # type: ignore

        assert "Can't instantiate abstract class" in str(exc_info.value)
        assert "load_model" in str(exc_info.value)

    def test_concrete_subclass_missing_unload_model_raises_type_error(self) -> None:
        """Test that a concrete subclass missing unload_model raises TypeError."""

        class IncompleteBackend(ModelBackend):
            """Incomplete backend missing unload_model."""

            async def load_model(self, model_name: str) -> None:
                pass

            async def get_available_memory(self) -> int:
                return 0

            async def get_active_model(self) -> str | None:
                return None

        with pytest.raises(TypeError) as exc_info:
            IncompleteBackend()  # type: ignore

        assert "Can't instantiate abstract class" in str(exc_info.value)
        assert "unload_model" in str(exc_info.value)

    def test_concrete_subclass_missing_get_available_memory_raises_type_error(
        self,
    ) -> None:
        """Test that concrete subclass missing get_available_memory raises TypeError."""

        class IncompleteBackend(ModelBackend):
            """Incomplete backend missing get_available_memory."""

            async def load_model(self, model_name: str) -> None:
                pass

            async def unload_model(self) -> None:
                pass

            async def get_active_model(self) -> str | None:
                return None

        with pytest.raises(TypeError) as exc_info:
            IncompleteBackend()  # type: ignore

        assert "Can't instantiate abstract class" in str(exc_info.value)
        assert "get_available_memory" in str(exc_info.value)

    def test_concrete_subclass_missing_get_active_model_raises_type_error(self) -> None:
        """Test that a concrete subclass missing get_active_model raises TypeError."""

        class IncompleteBackend(ModelBackend):
            """Incomplete backend missing get_active_model."""

            async def load_model(self, model_name: str) -> None:
                pass

            async def unload_model(self) -> None:
                pass

            async def get_available_memory(self) -> int:
                return 0

        with pytest.raises(TypeError) as exc_info:
            IncompleteBackend()  # type: ignore

        assert "Can't instantiate abstract class" in str(exc_info.value)
        assert "get_active_model" in str(exc_info.value)

    def test_complete_concrete_subclass_can_be_instantiated(self) -> None:
        """Test that a complete concrete subclass can be instantiated."""

        class ConcreteBackend(ModelBackend):
            """Complete backend implementation."""

            async def load_model(self, model_name: str) -> None:
                pass

            async def unload_model(self) -> None:
                pass

            async def get_available_memory(self) -> int:
                return 0

            async def get_active_model(self) -> str | None:
                return None

        backend = ConcreteBackend()
        assert isinstance(backend, ModelBackend)

    def test_backend_name_property_returns_class_name(self) -> None:
        """Test that backend_name property returns the class name."""

        class CustomBackend(ModelBackend):
            """Custom backend for testing."""

            async def load_model(self, model_name: str) -> None:
                pass

            async def unload_model(self) -> None:
                pass

            async def get_available_memory(self) -> int:
                return 0

            async def get_active_model(self) -> str | None:
                return None

        backend = CustomBackend()
        assert backend.backend_name == "CustomBackend"

    def test_backend_name_property_is_not_abstract(self) -> None:
        """Test that backend_name property is concrete and implemented in base class."""

        class ConcreteBackend(ModelBackend):
            """Complete backend implementation."""

            async def load_model(self, model_name: str) -> None:
                pass

            async def unload_model(self) -> None:
                pass

            async def get_available_memory(self) -> int:
                return 0

            async def get_active_model(self) -> str | None:
                return None

        backend = ConcreteBackend()
        # Should not raise AttributeError
        assert hasattr(backend, "backend_name")
        assert backend.backend_name == "ConcreteBackend"
