"""Example test demonstrating usage of shared fixtures and factories.

This test file shows various ways to use the new shared testing fixtures
and factory functions. It serves as both a test and documentation.
"""

import pytest
from testing import (
    make_exo_health_response,
    make_exo_response,
    make_mock_backend,
    make_mock_clutch,
    make_mock_infra_manager,
)

from llm_clutch.core.clutch import EngineState


class TestFixtureUsageExamples:
    """Examples of using the new shared fixtures."""

    @pytest.mark.asyncio
    async def test_with_fixture_directly(self, mock_clutch) -> None:
        """Test using the mock_clutch fixture directly."""
        # The fixture provides a fully configured, healthy clutch
        status = mock_clutch.status()
        assert status.state == EngineState.IDLE

    @pytest.mark.asyncio
    async def test_with_factory_low_memory(self) -> None:
        """Test creating a custom backend with low memory."""
        # Factory functions allow creating custom configurations
        backend = make_mock_backend(available_memory=1000)
        clutch = make_mock_clutch(backend=backend)

        # This clutch will fail memory checks for large models
        result = await clutch.rev_match(5000)
        assert result is False

    @pytest.mark.asyncio
    async def test_with_factory_failing_backend(self) -> None:
        """Test with a backend that fails to load models."""
        backend = make_mock_backend(should_load_fail=True)
        clutch = make_mock_clutch(backend=backend)

        # This should raise when trying to engage
        from llm_clutch.backend.exceptions import ModelLoadError

        with pytest.raises(ModelLoadError):
            await clutch.engage("llama-7b")

    @pytest.mark.asyncio
    async def test_with_custom_infra_single_node(
        self, mock_all_nodes_reachable
    ) -> None:
        """Test with a single-node infrastructure."""
        # Use the fixture to mock all nodes as reachable
        infra = make_mock_infra_manager(node_ips=["10.0.0.1"])
        clutch = make_mock_clutch(infra_manager=infra, min_nodes=1)

        # Verify the topology
        result = await clutch.rev_match(100000)
        assert result is True

    @pytest.mark.asyncio
    async def test_composability_custom_backend_and_infra(
        self, mock_all_nodes_reachable
    ) -> None:
        """Test combining custom backend and infrastructure."""
        backend = make_mock_backend(available_memory=10000000)  # 10MB
        infra = make_mock_infra_manager(node_ips=["10.0.0.1", "10.0.0.2", "10.0.0.3"])

        clutch = make_mock_clutch(backend=backend, infra_manager=infra, min_nodes=2)

        # Verify large model can fit
        result = await clutch.rev_match(5000000)  # 5MB
        assert result is True

    @pytest.mark.asyncio
    async def test_response_factory_usage(self) -> None:
        """Test using response factory functions."""
        # These can be used with respx for HTTP mocking
        success_response = make_exo_response(status=200, json_data={"status": "ok"})
        assert success_response.status_code == 200

        error_response = make_exo_response(status=500)
        assert error_response.status_code == 500

        health = make_exo_health_response(healthy=True)
        assert health["status"] == "healthy"


@pytest.mark.parametrize(
    "available_memory,required_memory,should_fit",
    [
        (1000000, 500000, True),  # 1MB available, 500KB required
        (500000, 500000, True),  # Exact fit
        (499999, 500000, False),  # Just under requirement
        (100000, 1000000, False),  # Way too small
    ],
)
@pytest.mark.asyncio
async def test_memory_thresholds_parametrized(
    available_memory: int,
    required_memory: int,
    should_fit: bool,
    mock_all_nodes_reachable,
) -> None:
    """Test rev_match with various memory amounts using parametrize."""
    backend = make_mock_backend(available_memory=available_memory)
    clutch = make_mock_clutch(backend=backend)

    result = await clutch.rev_match(required_memory)
    assert result == should_fit
