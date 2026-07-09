# API Reference: LLMClutch

The `LLMClutch` class is the main orchestrator for model shifting operations. It ties together the backend (model management) and infrastructure manager (cluster health) to provide safe, coordinated model transitions.

## LLMClutch

Main clutch engine orchestrator for LLM model management.

### Class Definition

```python
from llm_clutch import LLMClutch
from llm_clutch.backend.exo import ExoBackend
from llm_clutch.core.infra import InfraManager

backend = ExoBackend(base_url="http://10.0.0.1:52415")
infra = InfraManager(node_ips=["10.0.0.1", "10.0.0.2", "10.0.0.3"])
clutch = LLMClutch(backend=backend, infra_manager=infra)
```

### Constructor

```python
def __init__(
    self,
    backend: ModelBackend,
    infra_manager: InfraManager,
    min_nodes: int = 1,
) -> None:
```

**Parameters:**

- `backend` (`ModelBackend`) — Backend implementation for model management (e.g., `ExoBackend`)
- `infra_manager` (`InfraManager`) — Manager for cluster infrastructure health checks
- `min_nodes` (`int`, optional) — Minimum number of reachable nodes required before allowing shifts. Defaults to 1

**Example:**

```python
clutch = LLMClutch(
    backend=ExoBackend(base_url="http://10.0.0.1:52415"),
    infra_manager=InfraManager(node_ips=["10.0.0.1", "10.0.0.2"]),
    min_nodes=2  # Require at least 2 nodes before shifting
)
```

### Methods

#### `status()`

Get the current status of the clutch engine.

```python
def status() -> EngineStatus:
```

**Returns:**

`EngineStatus` object containing:
- `state` — Current engine state (`IDLE`, `SHIFTING`, `ENGAGED`, `ERROR`)
- `active_model` — Name of currently loaded model, or `None`
- `cluster_health` — Boolean indicating if cluster is healthy (at least `min_nodes` reachable)
- `last_shift_result` — Result of the last shift operation, or `None`

**Example:**

```python
status = clutch.status()
print(f"State: {status.state.value}")
print(f"Active model: {status.active_model}")
print(f"Healthy: {status.cluster_health}")
```

#### `upshift(heavy_model: str, required_ram: int) -> ShiftResult` *(async)*

Hot-swap from the current model to a heavier reasoning model.

```python
async def upshift(heavy_model: str, required_ram: int) -> ShiftResult:
```

**Parameters:**

- `heavy_model` (`str`) — Name of the heavier model to load (e.g., `"GPT-OSS-120B"`)
- `required_ram` (`int`) — Estimated RAM required (in bytes) for the new model

**Returns:**

`ShiftResult` containing:
- `success` — Whether the shift completed successfully
- `previous_model` — Model that was active before the shift
- `new_model` — Model that is now active
- `error` — Error message if failed, `None` otherwise
- `timestamp` — When the shift was attempted

**Raises:**

- `ValueError` — If cluster is unhealthy or has insufficient memory
- `ModelUnloadError` — If unloading the current model fails
- `ModelLoadError` — If loading the new model fails

**Example:**

```python
result = await clutch.upshift(
    heavy_model="GPT-OSS-120B",
    required_ram=75_000_000_000  # 75 GB
)

if result.success:
    print(f"Upshifted from {result.previous_model} to {result.new_model}")
else:
    print(f"Upshift failed: {result.error}")
```

#### `downshift(light_model: str, required_ram: int) -> ShiftResult` *(async)*

Hot-swap from the current model back to a lighter daily-driver model.

```python
async def downshift(light_model: str, required_ram: int) -> ShiftResult:
```

**Parameters:**

- `light_model` (`str`) — Name of the lighter model to load (e.g., `"Qwen3-Next-80B"`)
- `required_ram` (`int`) — Estimated RAM required (in bytes) for the new model

**Returns:**

`ShiftResult` — Same structure as `upshift()`

**Raises:**

- Same exceptions as `upshift()`

**Example:**

```python
result = await clutch.downshift(
    light_model="Qwen3-Next-80B",
    required_ram=50_000_000_000  # 50 GB
)
```

#### `emergency_reset() -> ShiftResult` *(async)*

Force-unload the current model without pre-flight checks. Use only when necessary to prevent cluster hangs.

```python
async def emergency_reset() -> ShiftResult:
```

**Returns:**

`ShiftResult` with `new_model` set to `None`

**Raises:**

- `ModelUnloadError` — If unloading fails

**Example:**

```python
# Use only in emergencies—bypasses health checks
result = await clutch.emergency_reset()
if result.success:
    print("Model unloaded successfully")
```

## Related Classes

### EngineState

Enum representing the current state of the clutch engine:

```python
class EngineState(Enum):
    IDLE = "idle"
    SHIFTING = "shifting"
    ENGAGED = "engaged"
    ERROR = "error"
```

### EngineStatus

Dataclass containing the current status snapshot:

```python
@dataclass
class EngineStatus:
    state: EngineState
    active_model: str | None
    cluster_health: bool
    last_shift_result: ShiftResult | None
```

### ShiftResult

Dataclass containing the result of a shift operation:

```python
@dataclass
class ShiftResult:
    success: bool
    previous_model: str | None
    new_model: str | None
    error: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
```

## Full Example

```python
import asyncio
from llm_clutch import LLMClutch
from llm_clutch.backend.exo import ExoBackend
from llm_clutch.core.infra import InfraManager

async def agent_workflow():
    # Setup
    backend = ExoBackend(base_url="http://10.0.0.1:52415")
    infra = InfraManager(node_ips=["10.0.0.1", "10.0.0.2", "10.0.0.3"])
    clutch = LLMClutch(backend=backend, infra_manager=infra, min_nodes=3)
    
    # Check status
    status = clutch.status()
    print(f"Starting state: {status.state.value}")
    print(f"Cluster healthy: {status.cluster_health}")
    
    # Run agent with fast model
    print("Running daily tasks with Qwen3-Next-80B...")
    # ... your agent code here ...
    
    # Upshift for complex reasoning
    print("Upshifting to GPT-OSS-120B for complex task...")
    result = await clutch.upshift(
        heavy_model="GPT-OSS-120B",
        required_ram=75_000_000_000
    )
    
    if not result.success:
        print(f"Failed to upshift: {result.error}")
        return
    
    # Run agent with reasoning model
    print("Running complex reasoning task...")
    # ... your agent code here ...
    
    # Downshift back to daily driver
    print("Downshifting back to Qwen3-Next-80B...")
    result = await clutch.downshift(
        light_model="Qwen3-Next-80B",
        required_ram=50_000_000_000
    )
    
    print("Done!")

# Run
asyncio.run(agent_workflow())
```

## Error Handling

All async methods can raise exceptions. Here's how to handle them robustly:

```python
from llm_clutch.backend.exceptions import (
    ModelLoadError,
    ModelUnloadError,
    BackendError,
)

async def safe_upshift(clutch: LLMClutch, model: str, ram: int):
    try:
        result = await clutch.upshift(model, ram)
        if not result.success:
            print(f"Upshift failed: {result.error}")
    except ValueError as e:
        # Cluster unhealthy or insufficient memory
        print(f"Pre-flight check failed: {e}")
    except ModelUnloadError as e:
        # Current model could not be unloaded
        print(f"Unload failed: {e}")
    except ModelLoadError as e:
        # New model could not be loaded
        print(f"Load failed: {e}")
    except BackendError as e:
        # Backend API error
        print(f"Backend error: {e}")
    except Exception as e:
        # Unexpected error
        print(f"Unexpected error: {e}")
```

See [Backend Reference](backend.md) for more details on backend exceptions and the `ModelBackend` interface.
