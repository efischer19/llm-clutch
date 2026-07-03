"""Abstract base class for LLM runner backends."""

from abc import ABC, abstractmethod


class ModelBackend(ABC):
    """Abstract base class defining the contract for all LLM runner backends.

    All concrete backend implementations must inherit from this class and
    implement all abstract methods. This interface allows llm-clutch to
    support multiple backends (Exo, future runners) without hardcoding
    to any specific one.
    """

    @property
    def backend_name(self) -> str:
        """Return the name of this backend implementation.

        Returns:
            str: The class name of the backend implementation.
        """
        return self.__class__.__name__

    @abstractmethod
    async def load_model(self, model_name: str) -> None:
        """Load model weights into cluster memory.

        Args:
            model_name: The name of the model to load.

        Raises:
            ModelLoadError: If model loading fails.
            InsufficientMemoryError: If there is insufficient memory to load the model.
        """
        pass

    @abstractmethod
    async def unload_model(self) -> None:
        """Unload the currently active model.

        Raises:
            ModelUnloadError: If model unloading fails.
        """
        pass

    @abstractmethod
    async def get_available_memory(self) -> int:
        """Return available unified memory in bytes across the cluster.

        Returns:
            int: Available memory in bytes.

        Raises:
            BackendError: If memory information cannot be retrieved.
        """
        pass

    @abstractmethod
    async def get_active_model(self) -> str | None:
        """Return the name of the currently loaded model, or None.

        Returns:
            str | None: The name of the active model, or None if no model is loaded.

        Raises:
            BackendError: If active model information cannot be retrieved.
        """
        pass
