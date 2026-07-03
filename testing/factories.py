"""Factory functions for creating mock objects and test data.

These factories allow tests to customize mock behavior per test case
without rebuilding the entire mock stack.
"""

from unittest.mock import AsyncMock

import httpx


def make_exo_response(
    status: int = 200,
    json_data: dict | None = None,
    delay: float = 0.0,
) -> httpx.Response:
    """Create a mock Exo API response.

    Args:
        status: HTTP status code (default 200).
        json_data: JSON response body (optional).
        delay: Artificial delay in seconds (optional).

    Returns:
        A configured httpx.Response mock.
    """
    response = httpx.Response(status_code=status, json=json_data or {})
    if delay > 0:
        response._delay = delay
    return response


def make_tcp_connection_mock(
    reachable: bool = True,
    delay: float = 0.0,
) -> AsyncMock:
    """Create a mock for asyncio.open_connection.

    Args:
        reachable: Whether the connection should succeed (default True).
        delay: Artificial delay in seconds (optional).

    Returns:
        An AsyncMock configured for socket connection behavior.
    """
    mock = AsyncMock()

    if reachable:
        reader_mock = AsyncMock()
        writer_mock = AsyncMock()
        writer_mock.wait_closed = AsyncMock()
        mock.return_value = (reader_mock, writer_mock)
    else:
        # Simulate connection refused
        mock.side_effect = ConnectionRefusedError("Connection refused")

    return mock


def make_node_status(
    ip: str,
    reachable: bool = True,
    latency_ms: float = 5.0,
) -> dict:
    """Create a node status dict for testing.

    Args:
        ip: Node IP address.
        reachable: Whether the node is reachable (default True).
        latency_ms: Latency in milliseconds (default 5.0).

    Returns:
        A dict with node status information.
    """
    return {
        "ip": ip,
        "reachable": reachable,
        "latency_ms": latency_ms if reachable else None,
    }


def make_exo_topology_response() -> dict:
    """Create a mock Exo topology response.

    Returns:
        A dict with topology information.
    """
    return {
        "nodes": [
            {
                "id": "node-0",
                "address": "10.0.0.1",
                "memory_bytes": 1000000,
                "status": "healthy",
            },
            {
                "id": "node-1",
                "address": "10.0.0.2",
                "memory_bytes": 1000000,
                "status": "healthy",
            },
        ],
        "total_memory": 2000000,
    }


def make_exo_health_response(healthy: bool = True) -> dict:
    """Create a mock Exo health check response.

    Args:
        healthy: Whether the cluster is healthy (default True).

    Returns:
        A dict with health information.
    """
    return {
        "status": "healthy" if healthy else "unhealthy",
        "timestamp": "2024-01-01T00:00:00Z",
    }


def make_exo_active_model_response(model_name: str | None = None) -> dict:
    """Create a mock Exo active model response.

    Args:
        model_name: The name of the active model (None if no model loaded).

    Returns:
        A dict with active model information.
    """
    if model_name is None:
        return {}
    return {"model_name": model_name}
