"""Shared pytest fixtures for testing llm-clutch components.

This module provides reusable fixtures for mocking the Exo API and
Thunderbolt network topology, enabling the full test suite to run without
physical hardware. These fixtures are designed to be composable —
individual tests can override specific behaviors without rebuilding the
entire mock stack.
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import respx

from llm_clutch.backend.base import ModelBackend
from llm_clutch.backend.exo import ExoBackend
from llm_clutch.core.clutch import LLMClutch
from llm_clutch.core.infra import InfraManager


class MockModelBackend(ModelBackend):
    """Configurable mock backend for testing.

    Allows tests to specify success/failure behavior, latency simulation,
    and specific return values for each operation.
    """

    def __init__(
        self,
        available_memory: int = 1000000,
        active_model: str | None = None,
        should_load_fail: bool = False,
        should_unload_fail: bool = False,
        should_memory_fail: bool = False,
        load_delay: float = 0.0,
        unload_delay: float = 0.0,
    ) -> None:
        """Initialize the mock backend.

        Args:
            available_memory: Bytes of available memory (default 1MB).
            active_model: Currently active model name (optional).
            should_load_fail: Whether load_model should raise an error.
            should_unload_fail: Whether unload_model should raise an error.
            should_memory_fail: Whether get_available_memory should fail.
            load_delay: Artificial delay for load_model in seconds.
            unload_delay: Artificial delay for unload_model in seconds.
        """
        self.available_memory = available_memory
        self.active_model = active_model
        self.should_load_fail = should_load_fail
        self.should_unload_fail = should_unload_fail
        self.should_memory_fail = should_memory_fail
        self.load_delay = load_delay
        self.unload_delay = unload_delay

    async def load_model(self, model_name: str) -> None:
        """Load model (optionally failing)."""
        if self.load_delay > 0:
            import asyncio

            await asyncio.sleep(self.load_delay)

        if self.should_load_fail:
            from llm_clutch.backend.exceptions import ModelLoadError

            raise ModelLoadError("Mock load failure")

        self.active_model = model_name

    async def unload_model(self) -> None:
        """Unload model (optionally failing)."""
        if self.unload_delay > 0:
            import asyncio

            await asyncio.sleep(self.unload_delay)

        if self.should_unload_fail:
            from llm_clutch.backend.exceptions import ModelUnloadError

            raise ModelUnloadError("Mock unload failure")

        self.active_model = None

    async def get_available_memory(self) -> int:
        """Get available memory (optionally failing)."""
        if self.should_memory_fail:
            from llm_clutch.backend.exceptions import BackendError

            raise BackendError("Mock memory retrieval failure")

        return self.available_memory

    async def get_active_model(self) -> str | None:
        """Get the currently active model."""
        return self.active_model


@pytest.fixture
def mock_exo_backend() -> MockModelBackend:
    """Provide a configurable mock ExoBackend for testing.

    By default, returns a healthy backend with 1MB of available memory.
    Tests can customize behavior by creating a new instance with different
    parameters.

    Example:
        def test_something(mock_exo_backend):
            # Use default behavior
            assert await mock_exo_backend.get_available_memory() == 1000000

        def test_memory_failure():
            # Create custom mock
            backend = MockModelBackend(should_memory_fail=True)
            # ... test with custom backend ...
    """
    return MockModelBackend()


@pytest.fixture
def mock_infra_manager() -> "InfraManager":
    """Provide a mock InfraManager with all nodes healthy.

    By default, simulates 3 nodes all reachable. Tests can customize
    node behavior by patching asyncio.open_connection directly or by
    creating a new InfraManager instance.

    Example:
        def test_cluster_healthy(mock_infra_manager):
            # Verify topology is healthy
            result = await mock_infra_manager.verify_topology(min_nodes=1)
            assert result is True
    """
    return InfraManager(
        node_ips=["10.0.0.1", "10.0.0.2", "10.0.0.3"],
        timeout_seconds=5,
        port=52415,
    )


@pytest.fixture
def mock_clutch(
    mock_exo_backend: MockModelBackend,
    mock_infra_manager: InfraManager,
) -> LLMClutch:
    """Provide a fully composed mock LLMClutch instance.

    Combines mock_exo_backend + mock_infra_manager into a testable
    LLMClutch instance. Tests can patch the fixture or components
    as needed for specific test scenarios.

    Example:
        def test_upshift(mock_clutch):
            result = await mock_clutch.upshift("llama-70b", 500000)
            assert result is not None
    """
    return LLMClutch(
        backend=mock_exo_backend,
        infra_manager=mock_infra_manager,
        min_nodes=1,
    )


@pytest.fixture
def mock_exo_http_backend(
    mock_exo_backend: MockModelBackend,
) -> "ExoBackend":
    """Provide an ExoBackend with mocked HTTP responses.

    Uses respx to mock HTTP calls to the Exo API. All common endpoints
    are mocked to return sensible defaults.

    Example:
        @pytest.mark.asyncio
        async def test_load_model(mock_exo_http_backend):
            async with mock_exo_http_backend:
                await mock_exo_http_backend.load_model("llama-7b")
                # HTTP calls are mocked, no real network traffic
    """
    return ExoBackend(
        base_url="http://127.0.0.1:52415",
        timeout_seconds=30,
    )


@pytest.fixture
def respx_mock() -> respx.MockRouter:
    """Provide a respx mock router for HTTP mocking.

    This fixture automatically applies respx mocking for the duration
    of the test and cleans up afterward.

    Example:
        @pytest.mark.asyncio
        async def test_api_call(respx_mock):
            respx_mock.get("/api/v1/health").mock(
                return_value=httpx.Response(200, json={"status": "ok"})
            )
            # ... test with mocked HTTP ...
    """
    with respx.mock:
        yield respx.mock


@pytest.fixture
def mock_tcp_connection() -> AsyncMock:
    """Provide a patchable mock for asyncio.open_connection.

    By default, simulates successful connections. Tests can configure
    specific behavior using the mock's return_value or side_effect.

    Example:
        @pytest.mark.asyncio
        async def test_node_reachable(mock_tcp_connection):
            with patch("asyncio.open_connection", mock_tcp_connection):
                manager = InfraManager(["10.0.0.1"])
                result = await manager.verify_topology()
                assert result is True
    """
    reader_mock = AsyncMock()
    writer_mock = AsyncMock()
    writer_mock.wait_closed = AsyncMock()

    mock = AsyncMock(return_value=(reader_mock, writer_mock))
    return mock


@pytest.fixture
def mock_all_nodes_reachable(mock_tcp_connection: AsyncMock) -> None:
    """Patch asyncio.open_connection to simulate all nodes reachable.

    This fixture automatically patches asyncio.open_connection for
    the duration of the test.
    """
    with patch("asyncio.open_connection", mock_tcp_connection):
        yield


@pytest.fixture
def mock_all_nodes_unreachable() -> None:
    """Patch asyncio.open_connection to simulate all nodes unreachable.

    This fixture automatically patches asyncio.open_connection to
    raise ConnectionRefusedError.
    """
    mock = AsyncMock(side_effect=ConnectionRefusedError("Connection refused"))
    with patch("asyncio.open_connection", mock):
        yield


def make_mock_backend(
    available_memory: int = 1000000,
    active_model: str | None = None,
    **kwargs: Any,
) -> MockModelBackend:
    """Create a configured MockModelBackend instance.

    This factory function allows tests to quickly create customized
    backend mocks without defining new fixtures.

    Args:
        available_memory: Available memory in bytes.
        active_model: Name of currently active model.
        **kwargs: Additional arguments passed to MockModelBackend.__init__.

    Returns:
        A configured MockModelBackend instance.

    Example:
        def test_low_memory():
            backend = make_mock_backend(available_memory=1000)
            assert await backend.get_available_memory() == 1000
    """
    return MockModelBackend(
        available_memory=available_memory,
        active_model=active_model,
        **kwargs,
    )


def make_mock_infra_manager(
    node_ips: list[str] | None = None,
    timeout_seconds: int = 5,
    port: int = 52415,
) -> InfraManager:
    """Create a configured InfraManager instance.

    This factory function allows tests to quickly create customized
    infrastructure managers.

    Args:
        node_ips: List of node IP addresses (default: 3-node cluster).
        timeout_seconds: Connection timeout in seconds.
        port: Port for TCP connections.

    Returns:
        A configured InfraManager instance.

    Example:
        def test_single_node():
            manager = make_mock_infra_manager(node_ips=["10.0.0.1"])
            statuses = await manager.check_all_nodes()
            assert len(statuses) == 1
    """
    if node_ips is None:
        node_ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

    return InfraManager(
        node_ips=node_ips,
        timeout_seconds=timeout_seconds,
        port=port,
    )


def make_mock_clutch(
    backend: ModelBackend | None = None,
    infra_manager: InfraManager | None = None,
    min_nodes: int = 1,
) -> LLMClutch:
    """Create a fully configured LLMClutch instance for testing.

    This factory function allows tests to quickly assemble a complete
    mock clutch with custom components.

    Args:
        backend: Backend instance (default: MockModelBackend).
        infra_manager: InfraManager instance (default: 3-node mock).
        min_nodes: Minimum nodes for topology checks.

    Returns:
        A configured LLMClutch instance.

    Example:
        def test_upshift():
            clutch = make_mock_clutch()
            result = await clutch.upshift("llama-70b", 500000)
            assert result is not None
    """
    if backend is None:
        backend = make_mock_backend()

    if infra_manager is None:
        infra_manager = make_mock_infra_manager()

    return LLMClutch(
        backend=backend,
        infra_manager=infra_manager,
        min_nodes=min_nodes,
    )
