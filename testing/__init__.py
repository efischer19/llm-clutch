"""Shared testing utilities and fixtures for llm-clutch.

This package provides reusable pytest fixtures and factory functions
for testing llm-clutch components without physical hardware.
"""

from testing.conftest import (
    MockModelBackend,
    make_mock_backend,
    make_mock_clutch,
    make_mock_infra_manager,
    mock_clutch,
    mock_exo_backend,
    mock_infra_manager,
)
from testing.factories import (
    make_exo_active_model_response,
    make_exo_health_response,
    make_exo_response,
    make_exo_topology_response,
    make_node_status,
    make_tcp_connection_mock,
)

__all__ = [
    "MockModelBackend",
    "make_mock_backend",
    "make_mock_clutch",
    "make_mock_infra_manager",
    "mock_clutch",
    "mock_exo_backend",
    "mock_infra_manager",
    "make_exo_active_model_response",
    "make_exo_health_response",
    "make_exo_response",
    "make_exo_topology_response",
    "make_node_status",
    "make_tcp_connection_mock",
]
