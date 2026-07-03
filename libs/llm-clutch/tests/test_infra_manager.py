"""Unit tests for the InfraManager class."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from llm_clutch.core.infra import InfraManager, NodeStatus


class TestNodeStatus:
    """Tests for NodeStatus dataclass."""

    def test_node_status_creation(self) -> None:
        """Test that NodeStatus can be created with all fields."""
        checked_at = datetime.now()
        status = NodeStatus(
            ip="10.0.0.1",
            reachable=True,
            latency_ms=42.5,
            checked_at=checked_at,
        )
        assert status.ip == "10.0.0.1"
        assert status.reachable is True
        assert status.latency_ms == 42.5
        assert status.checked_at == checked_at

    def test_node_status_unreachable(self) -> None:
        """Test NodeStatus for an unreachable node."""
        checked_at = datetime.now()
        status = NodeStatus(
            ip="10.0.0.2",
            reachable=False,
            latency_ms=None,
            checked_at=checked_at,
        )
        assert status.ip == "10.0.0.2"
        assert status.reachable is False
        assert status.latency_ms is None
        assert status.checked_at == checked_at


class TestInfraManagerInit:
    """Tests for InfraManager initialization."""

    def test_infra_manager_creation_with_ips(self) -> None:
        """Test InfraManager can be created with a list of IPs."""
        ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
        manager = InfraManager(ips)
        assert manager.node_ips == ips
        assert manager.timeout_seconds == 5
        assert manager.port == 52415

    def test_infra_manager_creation_with_custom_timeout(self) -> None:
        """Test InfraManager can be created with custom timeout."""
        ips = ["10.0.0.1"]
        manager = InfraManager(ips, timeout_seconds=10)
        assert manager.timeout_seconds == 10

    def test_infra_manager_creation_with_custom_port(self) -> None:
        """Test InfraManager can be created with custom port."""
        ips = ["10.0.0.1"]
        manager = InfraManager(ips, port=9090)
        assert manager.port == 9090


class TestCheckNode:
    """Tests for the check_node method."""

    @pytest.mark.asyncio
    async def test_check_node_success(self) -> None:
        """Test successful node check."""
        manager = InfraManager(["10.0.0.1"])

        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        with patch(
            "asyncio.open_connection",
            return_value=(mock_reader, mock_writer),
        ):
            status = await manager.check_node("10.0.0.1")

        assert status.ip == "10.0.0.1"
        assert status.reachable is True
        assert status.latency_ms is not None
        assert status.latency_ms >= 0
        assert status.checked_at is not None

    @pytest.mark.asyncio
    async def test_check_node_timeout(self) -> None:
        """Test node check with timeout."""
        manager = InfraManager(["10.0.0.1"], timeout_seconds=0.01)

        async def slow_connect(*args, **kwargs):  # type: ignore
            """Simulate a slow connection that will timeout."""
            await asyncio.sleep(10)
            # This will never be reached due to asyncio.wait_for timeout
            raise RuntimeError("Should not reach this")

        with patch("asyncio.open_connection", side_effect=slow_connect):
            status = await manager.check_node("10.0.0.1")

        assert status.ip == "10.0.0.1"
        assert status.reachable is False
        assert status.latency_ms is None

    @pytest.mark.asyncio
    async def test_check_node_connection_refused(self) -> None:
        """Test node check with connection refused error."""
        manager = InfraManager(["10.0.0.1"])

        with patch(
            "asyncio.open_connection",
            side_effect=ConnectionRefusedError("Connection refused"),
        ):
            status = await manager.check_node("10.0.0.1")

        assert status.ip == "10.0.0.1"
        assert status.reachable is False
        assert status.latency_ms is None

    @pytest.mark.asyncio
    async def test_check_node_host_unreachable(self) -> None:
        """Test node check with host unreachable error."""
        manager = InfraManager(["10.0.0.1"])

        with patch(
            "asyncio.open_connection",
            side_effect=OSError("Host unreachable"),
        ):
            status = await manager.check_node("10.0.0.1")

        assert status.ip == "10.0.0.1"
        assert status.reachable is False
        assert status.latency_ms is None


class TestCheckAllNodes:
    """Tests for the check_all_nodes method."""

    @pytest.mark.asyncio
    async def test_check_all_nodes_all_reachable(self) -> None:
        """Test checking all nodes when all are reachable."""
        manager = InfraManager(["10.0.0.1", "10.0.0.2", "10.0.0.3"])

        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        with patch(
            "asyncio.open_connection",
            return_value=(mock_reader, mock_writer),
        ):
            statuses = await manager.check_all_nodes()

        assert len(statuses) == 3
        assert all(s.reachable for s in statuses)
        assert statuses[0].ip == "10.0.0.1"
        assert statuses[1].ip == "10.0.0.2"
        assert statuses[2].ip == "10.0.0.3"

    @pytest.mark.asyncio
    async def test_check_all_nodes_partial_failure(self) -> None:
        """Test checking all nodes when some fail."""
        manager = InfraManager(["10.0.0.1", "10.0.0.2", "10.0.0.3"])

        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        def side_effect(*args, **kwargs):  # type: ignore
            if args[0] == "10.0.0.2":
                raise ConnectionRefusedError("Connection refused")
            return (mock_reader, mock_writer)

        with patch("asyncio.open_connection", side_effect=side_effect):
            statuses = await manager.check_all_nodes()

        assert len(statuses) == 3
        assert statuses[0].reachable is True
        assert statuses[1].reachable is False
        assert statuses[2].reachable is True

    @pytest.mark.asyncio
    async def test_check_all_nodes_all_unreachable(self) -> None:
        """Test checking all nodes when all are unreachable."""
        manager = InfraManager(["10.0.0.1", "10.0.0.2", "10.0.0.3"])

        with patch(
            "asyncio.open_connection",
            side_effect=OSError("Connection failed"),
        ):
            statuses = await manager.check_all_nodes()

        assert len(statuses) == 3
        assert all(not s.reachable for s in statuses)

    @pytest.mark.asyncio
    async def test_check_all_nodes_runs_concurrently(self) -> None:
        """Test that check_all_nodes runs checks concurrently."""
        manager = InfraManager(
            ["10.0.0.1", "10.0.0.2", "10.0.0.3"],
            timeout_seconds=1.0,
        )

        call_count = 0
        call_times = []

        async def tracked_connect(*args, **kwargs):  # type: ignore
            nonlocal call_count
            call_count += 1
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.1)
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_writer.wait_closed = AsyncMock()
            return (mock_reader, mock_writer)

        with patch("asyncio.open_connection", side_effect=tracked_connect):
            statuses = await manager.check_all_nodes()

        assert len(statuses) == 3
        assert call_count == 3
        # Check that calls happened roughly concurrently
        # (within 0.15 seconds of each other, not sequentially)
        time_diff = max(call_times) - min(call_times)
        assert time_diff < 0.15


class TestVerifyTopology:
    """Tests for the verify_topology method."""

    @pytest.mark.asyncio
    async def test_verify_topology_all_reachable_min_one(self) -> None:
        """Test topology verification when all nodes are reachable."""
        manager = InfraManager(["10.0.0.1", "10.0.0.2", "10.0.0.3"])

        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        with patch(
            "asyncio.open_connection",
            return_value=(mock_reader, mock_writer),
        ):
            is_healthy = await manager.verify_topology(min_nodes=1)

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_verify_topology_all_reachable_min_three(self) -> None:
        """Test topology verification with all nodes reachable and min_nodes=3."""
        manager = InfraManager(["10.0.0.1", "10.0.0.2", "10.0.0.3"])

        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        with patch(
            "asyncio.open_connection",
            return_value=(mock_reader, mock_writer),
        ):
            is_healthy = await manager.verify_topology(min_nodes=3)

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_verify_topology_partial_failure_meets_min(self) -> None:
        """Test topology verification when partial failure meets minimum."""
        manager = InfraManager(["10.0.0.1", "10.0.0.2", "10.0.0.3"])

        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        def side_effect(*args, **kwargs):  # type: ignore
            if args[0] == "10.0.0.3":
                raise OSError("Connection failed")
            return (mock_reader, mock_writer)

        with patch("asyncio.open_connection", side_effect=side_effect):
            is_healthy = await manager.verify_topology(min_nodes=2)

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_verify_topology_partial_failure_below_min(self) -> None:
        """Test topology verification when partial failure below minimum."""
        manager = InfraManager(["10.0.0.1", "10.0.0.2", "10.0.0.3"])

        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        def side_effect(*args, **kwargs):  # type: ignore
            if args[0] == "10.0.0.3":
                raise OSError("Connection failed")
            return (mock_reader, mock_writer)

        with patch("asyncio.open_connection", side_effect=side_effect):
            is_healthy = await manager.verify_topology(min_nodes=3)

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_verify_topology_all_unreachable(self) -> None:
        """Test topology verification when all nodes are unreachable."""
        manager = InfraManager(["10.0.0.1", "10.0.0.2", "10.0.0.3"])

        with patch(
            "asyncio.open_connection",
            side_effect=OSError("Connection failed"),
        ):
            is_healthy = await manager.verify_topology(min_nodes=1)

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_verify_topology_default_min_one(self) -> None:
        """Test topology verification uses default min_nodes=1."""
        manager = InfraManager(["10.0.0.1"])

        with patch(
            "asyncio.open_connection",
            side_effect=OSError("Connection failed"),
        ):
            # With only 1 node and all unreachable, should fail with min=1
            is_healthy = await manager.verify_topology()

        assert is_healthy is False


class TestInfraManagerIntegration:
    """Integration tests for InfraManager."""

    @pytest.mark.asyncio
    async def test_manager_with_empty_node_list(self) -> None:
        """Test that manager works with empty node list."""
        manager = InfraManager([])
        statuses = await manager.check_all_nodes()
        assert statuses == []

    @pytest.mark.asyncio
    async def test_manager_with_single_node(self) -> None:
        """Test manager with single node."""
        manager = InfraManager(["10.0.0.1"])

        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        with patch(
            "asyncio.open_connection",
            return_value=(mock_reader, mock_writer),
        ):
            is_healthy = await manager.verify_topology()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_multiple_checks_are_independent(self) -> None:
        """Test that multiple check_all_nodes calls are independent."""
        manager = InfraManager(["10.0.0.1", "10.0.0.2"])

        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        with patch(
            "asyncio.open_connection",
            return_value=(mock_reader, mock_writer),
        ):
            statuses1 = await manager.check_all_nodes()
            statuses2 = await manager.check_all_nodes()

        assert len(statuses1) == 2
        assert len(statuses2) == 2
        assert all(s.reachable for s in statuses1)
        assert all(s.reachable for s in statuses2)
        # Times should be different
        assert statuses1[0].checked_at != statuses2[0].checked_at
