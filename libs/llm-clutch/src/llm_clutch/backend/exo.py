"""Exo backend implementation for LLM cluster management."""

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from llm_clutch.backend.base import ModelBackend
from llm_clutch.backend.exceptions import (
    BackendError,
    ModelLoadError,
    ModelUnloadError,
)

logger = structlog.get_logger(__name__)

# Retry configuration for Tenacity
RETRY_CONFIG = {
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=1, max=10),
    "retry": retry_if_exception_type(
        (
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.HTTPStatusError,
        )
    ),
    "reraise": True,
}


class ExoBackend(ModelBackend):
    """Concrete backend implementation for Exo LLM runner clusters.

    Communicates with the Exo LLM runner's HTTP API to manage model
    lifecycle operations across the cluster. Includes automatic retry
    logic with exponential backoff for transient failures.

    Attributes:
        base_url: Base URL for the Exo API (e.g., "http://10.0.0.1:52415").
        timeout_seconds: Timeout in seconds for HTTP requests. Defaults to 30.
    """

    DEFAULT_TIMEOUT_SECONDS = 30

    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the ExoBackend.

        Args:
            base_url: Base URL for the Exo API (e.g., "http://10.0.0.1:52415").
            client: Optional httpx.AsyncClient instance. If not provided,
                one will be created and managed internally.
            timeout_seconds: Timeout in seconds for HTTP requests.
                Defaults to 30.

        Raises:
            ValueError: If base_url is empty.
        """
        if not base_url:
            raise ValueError("base_url cannot be empty")

        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._owned_client = client is None
        logger.debug(
            "exo_backend_initialized",
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            owns_client=self._owned_client,
        )

    async def __aenter__(self) -> "ExoBackend":
        """Enter async context manager, creating client if needed."""
        if self._owned_client and self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url)
            logger.debug("exo_backend_client_created")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Exit async context manager, closing client if owned."""
        if self._owned_client and self._client is not None:
            await self._client.aclose()
            logger.debug("exo_backend_client_closed")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.

        Returns:
            The httpx.AsyncClient instance to use for requests.

        Raises:
            RuntimeError: If client was not provided and context manager
                was not used.
        """
        if self._client is None:
            if self._owned_client:
                self._client = httpx.AsyncClient(base_url=self.base_url)
                logger.debug("exo_backend_client_created_on_demand")
            else:
                raise RuntimeError(
                    "ExoBackend client not initialized. "
                    "Either provide a client in __init__ or use "
                    "as async context manager."
                )
        return self._client

    async def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs,  # type: ignore
    ) -> httpx.Response:
        """Make an HTTP request with Tenacity retry logic.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path (e.g., "/api/v1/models/load").
            **kwargs: Additional arguments to pass to httpx.

        Returns:
            The httpx.Response object.

        Raises:
            httpx.ConnectError: On connection failures after all retries.
            httpx.TimeoutException: On timeout after all retries.
            httpx.HTTPStatusError: On HTTP 5xx after all retries.
        """
        client = await self._get_client()

        # Use AsyncRetrying to wrap the request with retry logic
        retrying = AsyncRetrying(**RETRY_CONFIG)

        async def request_with_status_check() -> httpx.Response:
            """Make the request and raise on 5xx status codes."""
            response = await client.request(
                method,
                endpoint,
                timeout=self.timeout_seconds,
                **kwargs,
            )
            # Raise on 5xx status codes to trigger retries
            if 500 <= response.status_code < 600:
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )
            return response

        # Execute with retries
        return await retrying(request_with_status_check)

    async def load_model(self, model_name: str) -> None:
        """Load model weights into the cluster.

        Calls the Exo API to load model weights. Includes automatic retry
        logic with exponential backoff for transient failures.

        Args:
            model_name: The name of the model to load
                (e.g., "meta-llama/Llama-2-7b").

        Raises:
            ModelLoadError: If model loading fails after all retries.
        """
        endpoint = "/api/v1/models/load"
        request_data = {"model_name": model_name}

        logger.info(
            "load_model_started",
            model_name=model_name,
            endpoint=endpoint,
        )

        try:
            response = await self._make_request_with_retry(
                "POST",
                endpoint,
                json=request_data,
            )
            response.raise_for_status()

            logger.info(
                "load_model_success",
                model_name=model_name,
                status_code=response.status_code,
            )
        except (
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.RequestError,
        ) as e:
            error_msg = f"Failed to load model '{model_name}': {str(e)}"
            logger.error(
                "load_model_failed",
                model_name=model_name,
                error=error_msg,
                exc_info=True,
            )
            raise ModelLoadError(error_msg) from e

    async def unload_model(self) -> None:
        """Unload the currently active model from the cluster.

        Calls the Exo API to unload the active model. Includes automatic retry
        logic with exponential backoff for transient failures.

        Raises:
            ModelUnloadError: If model unloading fails after all retries.
        """
        endpoint = "/api/v1/models/unload"

        logger.info(
            "unload_model_started",
            endpoint=endpoint,
        )

        try:
            response = await self._make_request_with_retry(
                "POST",
                endpoint,
            )
            response.raise_for_status()

            logger.info(
                "unload_model_success",
                status_code=response.status_code,
            )
        except (
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.RequestError,
        ) as e:
            error_msg = f"Failed to unload model: {str(e)}"
            logger.error(
                "unload_model_failed",
                error=error_msg,
                exc_info=True,
            )
            raise ModelUnloadError(error_msg) from e

    async def get_available_memory(self) -> int:
        """Query the cluster for total available memory in bytes.

        Queries Exo topology or health endpoints to determine total
        available RAM across the cluster.

        Returns:
            Total available memory in bytes across the cluster.

        Raises:
            BackendError: If memory information cannot be retrieved.
        """
        endpoint = "/api/v1/topology"

        logger.info(
            "get_available_memory_started",
            endpoint=endpoint,
        )

        try:
            response = await self._make_request_with_retry(
                "GET",
                endpoint,
            )
            response.raise_for_status()

            data = response.json()

            # TODO: Verify exact response format against live Exo cluster
            # Expected format: { "nodes": [{ "memory": 12345 }, ...] }
            # or similar structure with memory information per node.
            total_memory = 0
            if "nodes" in data and isinstance(data["nodes"], list):
                for node in data["nodes"]:
                    if "memory" in node:
                        total_memory += int(node["memory"])
            elif "total_memory" in data:
                total_memory = int(data["total_memory"])

            logger.info(
                "get_available_memory_success",
                total_memory_bytes=total_memory,
            )
            return total_memory
        except (
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.RequestError,
        ) as e:
            error_msg = f"Failed to get available memory: {str(e)}"
            logger.error(
                "get_available_memory_failed",
                error=error_msg,
                exc_info=True,
            )
            raise BackendError(error_msg) from e

    async def get_active_model(self) -> str | None:
        """Query the cluster for the currently loaded model.

        Queries Exo for the name of the currently loaded model.

        Returns:
            The name of the currently loaded model, or None if no model
            is currently loaded.

        Raises:
            BackendError: If active model information cannot be retrieved.
        """
        endpoint = "/api/v1/models/active"

        logger.debug(
            "get_active_model_started",
            endpoint=endpoint,
        )

        try:
            response = await self._make_request_with_retry(
                "GET",
                endpoint,
            )
            response.raise_for_status()

            data = response.json()

            # TODO: Verify exact response format against live Exo cluster
            # Expected format: { "model_name": "meta-llama/Llama-2-7b" }
            # or { "model": "meta-llama/Llama-2-7b" }
            model_name = data.get("model_name") or data.get("model")

            logger.info(
                "get_active_model_success",
                model_name=model_name,
            )
            return model_name
        except (
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.RequestError,
        ) as e:
            error_msg = f"Failed to get active model: {str(e)}"
            logger.error(
                "get_active_model_failed",
                error=error_msg,
                exc_info=True,
            )
            raise BackendError(error_msg) from e

    async def health_check(self) -> bool:
        """Check if the Exo API is responsive (non-abstract, Exo-specific).

        Performs a simple GET request to the health endpoint to verify
        the API is responsive.

        Returns:
            True if the API is responsive, False otherwise.
        """
        endpoint = "/api/v1/health"

        logger.debug(
            "health_check_started",
            endpoint=endpoint,
        )

        try:
            response = await self._make_request_with_retry(
                "GET",
                endpoint,
            )
            is_healthy = response.status_code == 200
            logger.info(
                "health_check_completed",
                status_code=response.status_code,
                is_healthy=is_healthy,
            )
            return is_healthy
        except (
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.RequestError,
        ) as e:
            logger.warning(
                "health_check_failed",
                error=str(e),
            )
            return False
