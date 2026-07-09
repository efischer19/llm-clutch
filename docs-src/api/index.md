# API Reference

The llm-clutch API provides Python classes and async methods for programmatic model management.

## Core Classes

### [LLMClutch](clutch.md)

The main orchestrator for model shifting operations.

```python
from llm_clutch import LLMClutch

clutch = LLMClutch(backend=backend, infra_manager=infra)
result = await clutch.upshift(heavy_model, required_ram)
```

**Key Methods:**
- `status()` — Get current cluster and model state
- `upshift(heavy_model, required_ram)` — Shift to a heavier model
- `downshift(light_model, required_ram)` — Shift to a lighter model
- `emergency_reset()` — Force-unload model and restore to known state

[Full LLMClutch Reference →](clutch.md)

### [ModelBackend](backend.md)

Abstract base class for LLM runner backends.

```python
from llm_clutch.backend.base import ModelBackend

class MyBackend(ModelBackend):
    async def load_model(self, model_name: str) -> None: ...
    async def unload_model(self) -> None: ...
    async def get_available_memory(self) -> int: ...
    async def get_active_model(self) -> str | None: ...
```

**Built-in Implementations:**
- `ExoBackend` — For [Exo](https://github.com/exo-explore/exo) LLM clusters

[Full Backend Reference →](backend.md)

### [InfraManager](infra.md)

Manager for cluster infrastructure health checks.

```python
from llm_clutch.core.infra import InfraManager

infra = InfraManager(node_ips=["10.0.0.1", "10.0.0.2"])
statuses = await infra.check_all_nodes()
healthy = await infra.is_healthy(min_reachable=2)
```

**Key Methods:**
- `check_node(ip)` — Check a single node's reachability
- `check_all_nodes()` — Check all nodes in parallel
- `is_healthy(min_reachable)` — Verify minimum cluster health
- `get_healthy_nodes()` — Get list of reachable nodes

[Full InfraManager Reference →](infra.md)

## Data Classes

### EngineStatus

Current snapshot of the clutch engine state.

```python
@dataclass
class EngineStatus:
    state: EngineState              # IDLE, SHIFTING, ENGAGED, ERROR
    active_model: str | None        # Current model, or None
    cluster_health: bool            # Cluster is healthy
    last_shift_result: ShiftResult | None
```

### EngineState

Enum representing the engine's lifecycle state:

```python
class EngineState(Enum):
    IDLE = "idle"
    SHIFTING = "shifting"
    ENGAGED = "engaged"
    ERROR = "error"
```

### ShiftResult

Result of a shift operation (upshift/downshift/emergency_reset).

```python
@dataclass
class ShiftResult:
    success: bool
    previous_model: str | None
    new_model: str | None
    error: str | None = None
    timestamp: datetime = ...
```

### NodeStatus

Result of a single cluster node health check.

```python
@dataclass
class NodeStatus:
    ip: str
    reachable: bool
    latency_ms: float | None
    checked_at: datetime
```

## Quick Start Examples

### Basic Model Shifting

```python
import asyncio
from llm_clutch import LLMClutch
from llm_clutch.backend.exo import ExoBackend
from llm_clutch.core.infra import InfraManager

async def main():
    # Setup
    backend = ExoBackend(base_url="http://10.0.0.1:52415")
    infra = InfraManager(node_ips=["10.0.0.1", "10.0.0.2"])
    clutch = LLMClutch(backend=backend, infra_manager=infra)
    
    # Check status
    status = clutch.status()
    print(f"Current model: {status.active_model}")
    
    # Upshift to reasoning model
    result = await clutch.upshift(
        heavy_model="GPT-OSS-120B",
        required_ram=75_000_000_000
    )
    
    if result.success:
        print(f"Loaded {result.new_model}")

asyncio.run(main())
```

### Cluster Health Monitoring

```python
import asyncio
from llm_clutch.core.infra import InfraManager

async def monitor_health():
    infra = InfraManager(node_ips=["10.0.0.1", "10.0.0.2", "10.0.0.3"])
    
    statuses = await infra.check_all_nodes()
    for status in statuses:
        health = "✓" if status.reachable else "✗"
        latency = f"{status.latency_ms:.1f} ms" if status.latency_ms else "N/A"
        print(f"{health} {status.ip} ({latency})")

asyncio.run(monitor_health())
```

### Implementing a Custom Backend

```python
from llm_clutch.backend.base import ModelBackend
from llm_clutch.backend.exceptions import ModelLoadError, ModelUnloadError

class CustomBackend(ModelBackend):
    async def load_model(self, model_name: str) -> None:
        # Implement model loading logic
        pass
    
    async def unload_model(self) -> None:
        # Implement model unloading logic
        pass
    
    async def get_available_memory(self) -> int:
        # Return available memory in bytes
        return 100_000_000_000
    
    async def get_active_model(self) -> str | None:
        # Return currently active model name
        return None
```

## Error Handling

All llm-clutch operations can raise exceptions. Use try/except to handle errors gracefully:

```python
from llm_clutch.backend.exceptions import (
    ModelLoadError,
    ModelUnloadError,
    BackendError,
)

async def safe_upshift(clutch, model, ram):
    try:
        result = await clutch.upshift(model, ram)
        if not result.success:
            print(f"Upshift failed: {result.error}")
    except ValueError:
        print("Configuration error")
    except ModelLoadError:
        print("Model loading failed")
    except ModelUnloadError:
        print("Model unloading failed")
    except BackendError:
        print("Backend error")
```

## See Also

- [CLI Reference](../cli.md) — Command-line interface
- [Configuration Guide](../config.md) — Setup and configuration
- [Hardware Guide](../HARDWARE_GUIDE.md) — Infrastructure setup
