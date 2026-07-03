# llm-clutch — Testing

This directory contains shared testing utilities and fixtures for
**llm-clutch** and other applications in the monorepo.

## Purpose

The `testing/` directory provides reusable test infrastructure that can be
shared across multiple applications and libraries in the monorepo. This
avoids duplicating common test helpers and promotes consistent testing
patterns.

## Structure

```text
testing/
├── README.md              # This file
├── __init__.py            # Package initialization with exports
├── conftest.py            # Shared pytest fixtures
├── factories.py           # Test data factories
```

## Fixtures

### Mock Backends

- **`mock_exo_backend`**: A configurable mock ExoBackend for testing.
  - Returns a healthy backend with 1MB of available memory by default.
  - Customize behavior with: `MockModelBackend(available_memory=..., should_load_fail=True, etc.)`

- **`mock_infra_manager`**: A mock InfraManager with 3 nodes, all healthy by default.
  - Customize nodes with: `make_mock_infra_manager(node_ips=['10.0.0.1', ...])`

- **`mock_clutch`**: A fully composed LLMClutch instance for end-to-end testing.
  - Combines `mock_exo_backend` + `mock_infra_manager`.

### Network Mocking

- **`mock_tcp_connection`**: A patchable AsyncMock for `asyncio.open_connection`.
  - Use with: `patch("asyncio.open_connection", mock_tcp_connection)`

- **`mock_all_nodes_reachable`**: Fixture that patches all TCP connections to succeed.

- **`mock_all_nodes_unreachable`**: Fixture that patches all TCP connections to fail.

### HTTP Mocking

- **`mock_exo_http_backend`**: An ExoBackend with mocked HTTP responses via respx.

- **`respx_mock`**: Direct access to respx mock router for custom HTTP mocking.

## Factory Functions

### Backend Factories

```python
from testing import make_mock_backend, make_mock_infra_manager, make_mock_clutch

# Create a low-memory backend
backend = make_mock_backend(available_memory=1000)

# Create a backend that fails on load
backend = make_mock_backend(should_load_fail=True)

# Create an infrastructure manager with custom nodes
infra = make_mock_infra_manager(node_ips=["10.0.0.1"])

# Create a fully configured clutch
clutch = make_mock_clutch(min_nodes=2)
```

### Response Factories

```python
from testing import (
    make_exo_response,
    make_tcp_connection_mock,
    make_exo_topology_response,
    make_exo_health_response,
    make_exo_active_model_response,
)

# Create Exo API responses
response = make_exo_response(status=200, json_data={"model": "llama-7b"})
response = make_exo_response(status=500)  # Server error

# Create network mocks
connection_mock = make_tcp_connection_mock(reachable=True)
connection_mock = make_tcp_connection_mock(reachable=False)  # Connection refused

# Create Exo endpoint responses
topology = make_exo_topology_response()
health = make_exo_health_response(healthy=True)
model = make_exo_active_model_response(model_name="llama-7b")
```

## Usage Examples

### Testing with Fixtures

```python
import pytest
from testing import mock_clutch, make_mock_backend

@pytest.mark.asyncio
async def test_upshift_with_sufficient_memory(mock_clutch):
    """Test upshift operation."""
    result = await mock_clutch.upshift("llama-70b", 500000)
    assert result is not None

@pytest.mark.asyncio
async def test_upshift_with_custom_backend():
    """Test with a custom backend configuration."""
    backend = make_mock_backend(available_memory=1000)
    infra = make_mock_infra_manager()
    clutch = make_mock_clutch(backend=backend, infra_manager=infra)
    
    # Test with low memory
    result = await clutch.rev_match(500000)
    assert result is False
```

### Parametrized Tests

```python
import pytest
from testing import make_mock_backend

@pytest.mark.parametrize("available_memory,should_fit", [
    (1000000, True),   # 1MB
    (100000, False),   # 100KB
    (5000, False),     # 5KB
])
@pytest.mark.asyncio
async def test_memory_thresholds(available_memory, should_fit):
    """Test rev_match with various memory amounts."""
    backend = make_mock_backend(available_memory=available_memory)
    # ... rest of test
```

### Network Mocking

```python
import pytest
from unittest.mock import patch
from testing import mock_tcp_connection

@pytest.mark.asyncio
async def test_nodes_reachable(mock_tcp_connection):
    """Test with all nodes reachable."""
    with patch("asyncio.open_connection", mock_tcp_connection):
        # All connections will succeed
        manager = InfraManager(["10.0.0.1", "10.0.0.2"])
        result = await manager.verify_topology()
        assert result is True
```

### HTTP Mocking with respx

```python
import pytest
import httpx
from testing import respx_mock, make_exo_response

@pytest.mark.asyncio
async def test_exo_api_call(respx_mock):
    """Test ExoBackend with mocked HTTP responses."""
    respx_mock.post("/api/v1/models/load").mock(
        return_value=make_exo_response(status=200)
    )
    respx_mock.post("/api/v1/models/unload").mock(
        return_value=make_exo_response(status=200)
    )
    
    backend = ExoBackend("http://localhost:52415")
    async with backend:
        await backend.load_model("llama-7b")
        # HTTP calls are mocked, no real network traffic
```

## Conventions

- Shared fixtures and helpers live here; application-specific tests stay in
  their respective `tests/` directories
- Follow the [Development Philosophy](../meta/DEVELOPMENT_PHILOSOPHY.md) for
  testing standards
- Use pytest as the test framework
  (see [ADR-004](../meta/adr/ADR-004-use_pytest.md))
- Keep test utilities focused and well-documented
- Fixtures should be composable — tests should override specific behaviors
  without rebuilding the entire mock stack

