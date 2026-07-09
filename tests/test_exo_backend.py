"""Unit tests for the ExoBackend class."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from llm_clutch.backend.exceptions import (
    BackendError,
    ModelLoadError,
    ModelUnloadError,
)
from llm_clutch.backend.exo import ExoBackend


class TestExoBackendInit:
    """Tests for ExoBackend initialization."""

    def test_exo_backend_init_with_base_url(self) -> None:
        """Test ExoBackend can be initialized with a base URL."""
        backend = ExoBackend("http://10.0.0.1:52415")
        assert backend.base_url == "http://10.0.0.1:52415"
        assert backend.timeout_seconds == ExoBackend.DEFAULT_TIMEOUT_SECONDS

    def test_exo_backend_init_with_custom_timeout(self) -> None:
        """Test ExoBackend can be initialized with a custom timeout."""
        backend = ExoBackend("http://10.0.0.1:52415", timeout_seconds=60)
        assert backend.timeout_seconds == 60

    def test_exo_backend_init_with_provided_client(self) -> None:
        """Test ExoBackend can be initialized with a provided httpx client."""
        client = httpx.AsyncClient()
        backend = ExoBackend("http://10.0.0.1:52415", client=client)
        assert backend._client is client
        assert backend._owned_client is False

    def test_exo_backend_init_without_client(self) -> None:
        """Test ExoBackend without provided client creates its own."""
        backend = ExoBackend("http://10.0.0.1:52415")
        assert backend._client is None
        assert backend._owned_client is True

    def test_exo_backend_init_with_empty_url_raises_error(self) -> None:
        """Test that empty base URL raises ValueError."""
        with pytest.raises(ValueError, match="base_url cannot be empty"):
            ExoBackend("")

    def test_backend_name_property(self) -> None:
        """Test that backend_name property returns correct class name."""
        backend = ExoBackend("http://10.0.0.1:52415")
        assert backend.backend_name == "ExoBackend"


class TestExoBackendContextManager:
    """Tests for ExoBackend async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_creates_client(self) -> None:
        """Test that context manager creates a client."""
        backend = ExoBackend("http://10.0.0.1:52415")
        assert backend._client is None

        async with backend:
            assert backend._client is not None
            assert isinstance(backend._client, httpx.AsyncClient)

        # Client should be closed after exiting context
        assert backend._client is None or backend._client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_reuses_provided_client(self) -> None:
        """Test that context manager doesn't close a provided client."""
        client = httpx.AsyncClient()
        backend = ExoBackend("http://10.0.0.1:52415", client=client)

        async with backend:
            assert backend._client is client

        # Provided client should not be closed by context manager
        assert not client.is_closed

        await client.aclose()

    @pytest.mark.asyncio
    async def test_context_manager_exception_handling(self) -> None:
        """Test that context manager closes client even on exception."""
        backend = ExoBackend("http://10.0.0.1:52415")

        with pytest.raises(ValueError):
            async with backend:
                assert backend._client is not None
                raise ValueError("Test error")

        # Client should still be closed
        assert backend._client is None or backend._client.is_closed


class TestLoadModel:
    """Tests for load_model method."""

    @pytest.mark.asyncio
    async def test_load_model_success(self) -> None:
        """Test successful model loading."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            await backend.load_model("meta-llama/Llama-2-7b")

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0] == ("POST", "/api/v1/models/load")
            assert call_args[1]["json"] == {"model_name": "meta-llama/Llama-2-7b"}

    @pytest.mark.asyncio
    async def test_load_model_connection_error(self) -> None:
        """Test load_model raises ModelLoadError on connection failure."""
        backend = ExoBackend("http://10.0.0.1:52415")

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(ModelLoadError, match="Failed to load model"):
                await backend.load_model("meta-llama/Llama-2-7b")

    @pytest.mark.asyncio
    async def test_load_model_timeout_error(self) -> None:
        """Test load_model raises ModelLoadError on timeout."""
        backend = ExoBackend("http://10.0.0.1:52415")

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(ModelLoadError, match="Failed to load model"):
                await backend.load_model("meta-llama/Llama-2-7b")

    @pytest.mark.asyncio
    async def test_load_model_http_error(self) -> None:
        """Test load_model raises ModelLoadError on HTTP error."""
        backend = ExoBackend("http://10.0.0.1:52415")

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "HTTP 500", request=MagicMock(), response=MagicMock()
            )
            mock_request.return_value = mock_response

            with pytest.raises(ModelLoadError, match="Failed to load model"):
                await backend.load_model("meta-llama/Llama-2-7b")


class TestUnloadModel:
    """Tests for unload_model method."""

    @pytest.mark.asyncio
    async def test_unload_model_success(self) -> None:
        """Test successful model unloading."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            await backend.unload_model()

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0] == ("POST", "/api/v1/models/unload")

    @pytest.mark.asyncio
    async def test_unload_model_connection_error(self) -> None:
        """Test unload_model raises ModelUnloadError on connection failure."""
        backend = ExoBackend("http://10.0.0.1:52415")

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(ModelUnloadError, match="Failed to unload model"):
                await backend.unload_model()

    @pytest.mark.asyncio
    async def test_unload_model_timeout_error(self) -> None:
        """Test unload_model raises ModelUnloadError on timeout."""
        backend = ExoBackend("http://10.0.0.1:52415")

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(ModelUnloadError, match="Failed to unload model"):
                await backend.unload_model()


class TestGetAvailableMemory:
    """Tests for get_available_memory method."""

    @pytest.mark.asyncio
    async def test_get_available_memory_success_with_nodes(self) -> None:
        """Test successful memory retrieval with nodes format."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "nodes": [
                {"memory": 1000000},
                {"memory": 2000000},
                {"memory": 3000000},
            ]
        }

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            memory = await backend.get_available_memory()

            assert memory == 6000000
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0] == ("GET", "/api/v1/topology")

    @pytest.mark.asyncio
    async def test_get_available_memory_success_with_total(self) -> None:
        """Test successful memory retrieval with total_memory format."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"total_memory": 5000000}

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            memory = await backend.get_available_memory()

            assert memory == 5000000

    @pytest.mark.asyncio
    async def test_get_available_memory_connection_error(self) -> None:
        """Test get_available_memory raises BackendError on connection failure."""
        backend = ExoBackend("http://10.0.0.1:52415")

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(BackendError, match="Failed to get available memory"):
                await backend.get_available_memory()

    @pytest.mark.asyncio
    async def test_get_available_memory_empty_response(self) -> None:
        """Test get_available_memory returns 0 for empty response."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {}

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            memory = await backend.get_available_memory()

            assert memory == 0


class TestGetActiveModel:
    """Tests for get_active_model method."""

    @pytest.mark.asyncio
    async def test_get_active_model_success_with_model_name(self) -> None:
        """Test successful active model retrieval with model_name key."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"model_name": "meta-llama/Llama-2-7b"}

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            model = await backend.get_active_model()

            assert model == "meta-llama/Llama-2-7b"
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0] == ("GET", "/api/v1/models/active")

    @pytest.mark.asyncio
    async def test_get_active_model_success_with_model_key(self) -> None:
        """Test successful active model retrieval with model key."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"model": "meta-llama/Llama-2-7b"}

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            model = await backend.get_active_model()

            assert model == "meta-llama/Llama-2-7b"

    @pytest.mark.asyncio
    async def test_get_active_model_no_model_loaded(self) -> None:
        """Test get_active_model returns None when no model is loaded."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {}

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            model = await backend.get_active_model()

            assert model is None

    @pytest.mark.asyncio
    async def test_get_active_model_connection_error(self) -> None:
        """Test get_active_model raises BackendError on connection failure."""
        backend = ExoBackend("http://10.0.0.1:52415")

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(BackendError, match="Failed to get active model"):
                await backend.get_active_model()


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        """Test successful health check."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            is_healthy = await backend.health_check()

            assert is_healthy is True
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0] == ("GET", "/api/v1/health")

    @pytest.mark.asyncio
    async def test_health_check_non_200_response(self) -> None:
        """Test health check with non-200 status code."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            is_healthy = await backend.health_check()

            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self) -> None:
        """Test health check returns False on connection failure."""
        backend = ExoBackend("http://10.0.0.1:52415")

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = httpx.ConnectError("Connection failed")

            is_healthy = await backend.health_check()

            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_timeout(self) -> None:
        """Test health check returns False on timeout."""
        backend = ExoBackend("http://10.0.0.1:52415")

        with patch.object(
            backend, "_make_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Request timeout")

            is_healthy = await backend.health_check()

            assert is_healthy is False


class TestMakeRequestWithRetry:
    """Tests for retry logic in _make_request_with_retry."""

    @pytest.mark.asyncio
    async def test_make_request_with_retry_success_on_first_attempt(self) -> None:
        """Test successful request on first attempt."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.request = AsyncMock(return_value=mock_response)
        backend._client = mock_client

        response = await backend._make_request_with_retry("GET", "/api/v1/health")

        assert response.status_code == 200
        mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_on_5xx_status(self) -> None:
        """Test retry on 5xx status code."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        # First attempt returns 500, second returns 200
        mock_response_error = MagicMock()
        mock_response_error.status_code = 500
        mock_response_error.request = MagicMock()
        mock_response_error.response = MagicMock()

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200

        mock_client.request = AsyncMock(
            side_effect=[mock_response_error, mock_response_success]
        )
        backend._client = mock_client

        response = await backend._make_request_with_retry("GET", "/api/v1/health")

        assert response.status_code == 200
        # Should be called twice due to retry on 5xx
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_make_request_with_retry_on_connect_error(self) -> None:
        """Test retry on connection error."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        mock_response = MagicMock()
        mock_response.status_code = 200

        # First attempt raises ConnectError, second succeeds
        mock_client.request = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection failed"),
                mock_response,
            ]
        )
        backend._client = mock_client

        response = await backend._make_request_with_retry("GET", "/api/v1/health")

        assert response.status_code == 200
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_make_request_with_retry_all_attempts_fail(self) -> None:
        """Test that exception is raised after all retries exhausted."""
        backend = ExoBackend("http://10.0.0.1:52415")
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        # All attempts fail
        mock_client.request = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )
        backend._client = mock_client

        with pytest.raises(httpx.ConnectError):
            await backend._make_request_with_retry("GET", "/api/v1/health")

        # Should attempt 3 times
        assert mock_client.request.call_count == 3
