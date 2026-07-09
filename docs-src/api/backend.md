# API Reference: Backend Interfaces

This document covers the abstract `ModelBackend` interface and the concrete `ExoBackend` implementation.

## ModelBackend (Abstract)

Abstract base class that defines the contract for all LLM runner backends.

All concrete backend implementations must inherit from `ModelBackend` and implement all abstract methods. This allows llm-clutch to support multiple backends (Exo, vLLM, TensorRT, etc.) without hardcoding to any specific one.

### Class Definition

```python
from abc import ABC, abstractmethod

class ModelBackend(ABC):
    """Abstract base class for LLM runner backends."""
```

### Property

#### `backend_name`

```python
@property
def backend_name(self) -> str:
```

**Returns:** The name of the backend implementation (typically the class name).

**Example:**

```python
backend = ExoBackend(base_url="http://10.0.0.1:52415")
print(backend.backend_name)  # Output: "ExoBackend"
```

### Abstract Methods (Must Implement)

#### `load_model(model_name: str) -> None` *(async)*

Load model weights into cluster memory.

```python
@abstractmethod
async def load_model(self, model_name: str) -> None:
```

**Parameters:**

- `model_name` (`str`) — The name of the model to load (e.g., `"GPT-OSS-120B"`, `"Qwen3-Next-80B"`)

**Raises:**

- `ModelLoadError` — If model loading fails
- `InsufficientMemoryError` — If there is insufficient memory to load the model

**Example Implementation:**

```python
async def load_model(self, model_name: str) -> None:
    # 1. Query backend for available memory
    # 2. Check if model fits
    # 3. Send load command to backend
    # 4. Wait for model to be ready
    # 5. Verify load was successful
```

#### `unload_model() -> None` *(async)*

Unload the currently active model from memory.

```python
@abstractmethod
async def unload_model(self) -> None:
```

**Raises:**

- `ModelUnloadError` — If model unloading fails

**Example Implementation:**

```python
async def unload_model(self) -> None:
    # 1. Send unload command to backend
    # 2. Wait for model to be released
    # 3. Verify memory is freed
```

#### `get_available_memory() -> int` *(async)*

Return available unified memory in bytes across the cluster.

```python
@abstractmethod
async def get_available_memory(self) -> int:
```

**Returns:** Available memory in bytes (e.g., `75_000_000_000` for 75 GB)

**Raises:**

- `BackendError` — If memory information cannot be retrieved

**Example:**

```python
available_bytes = await backend.get_available_memory()
print(f"Available: {available_bytes / 1e9:.1f} GB")
```

#### `get_active_model() -> str | None` *(async)*

Return the name of the currently loaded model, or `None` if no model is active.

```python
@abstractmethod
async def get_active_model(self) -> str | None:
```

**Returns:** Model name string, or `None`

**Raises:**

- `BackendError` — If model information cannot be retrieved

**Example:**

```python
active = await backend.get_active_model()
print(f"Current model: {active or 'None'}")
```

## ExoBackend

Concrete backend implementation for [Exo](https://github.com/exo-explore/exo) LLM runner clusters.

Communicates with Exo's HTTP API to manage model lifecycle operations across the cluster. Includes automatic retry logic with exponential backoff for transient failures.

### Class Definition

```python
from llm_clutch.backend.exo import ExoBackend

backend = ExoBackend(base_url="http://10.0.0.1:52415")
```

### Constructor

```python
def __init__(
    self,
    base_url: str,
    client: httpx.AsyncClient | None = None,
    timeout_seconds: float = 30,
) -> None:
```

**Parameters:**

- `base_url` (`str`) — Base URL for the Exo API (e.g., `"http://10.0.0.1:52415"`)
- `client` (`httpx.AsyncClient | None`, optional) — Optional httpx.AsyncClient instance. If not provided, one will be created and managed internally
- `timeout_seconds` (`float`, optional) — Timeout in seconds for HTTP requests. Defaults to 30

**Raises:**

- `ValueError` — If `base_url` is empty

**Example:**

```python
import httpx

# Simple usage (client created internally)
backend = ExoBackend(base_url="http://10.0.0.1:52415")

# Advanced usage (with custom client)
async with httpx.AsyncClient() as client:
    backend = ExoBackend(
        base_url="http://10.0.0.1:52415",
        client=client,
        timeout_seconds=60
    )
```

### Attributes

- `base_url` (`str`) — The Exo API base URL
- `timeout_seconds` (`float`) — Request timeout in seconds
- `DEFAULT_TIMEOUT_SECONDS` (`int`) — Class constant set to 30

### Methods

All methods listed in `ModelBackend` are implemented. See the abstract class documentation above for the interface contract.

### Retry Behavior

ExoBackend automatically retries failed requests with exponential backoff:

- **Max attempts:** 3
- **Initial wait:** 1 second
- **Max wait:** 10 seconds
- **Retried on:**
  - `httpx.ConnectError` (connection issues)
  - `httpx.TimeoutException` (timeout)
  - HTTP 5xx responses (server errors)

This ensures temporary network glitches or transient backend issues don't immediately fail model operations.

### Exo API Integration

ExoBackend makes the following assumptions about your Exo deployment:

1. **Model loading endpoint:** `GET /compute/node/status` to check available memory and system status
2. **Model management:** Uses Exo's model lifecycle APIs to load/unload models
3. **Default port:** 52415 (Exo's default HTTP API port)

Ensure your Exo cluster is configured to expose these endpoints.

**Example Exo configuration:**

```bash
# Start Exo with HTTP API enabled
export EXO_API_HOST="0.0.0.0"
export EXO_API_PORT="52415"
uv run exo
```

### Error Handling

ExoBackend can raise the following exceptions (or subclasses):

| Exception | When | Solution |
| --- | --- | --- |
| `ModelLoadError` | Failed to load a model | Check Exo logs; verify model exists; ensure sufficient disk space on nodes |
| `ModelUnloadError` | Failed to unload a model | Restart Exo or use emergency reset; check cluster health |
| `BackendError` | Generic backend error (connection, API error) | Check Exo is running; verify network connectivity; check API endpoint |
| `ValueError` | Invalid base_url or configuration | Provide valid Exo API URL |

## Implementing a Custom Backend

To add support for a different LLM runner (e.g., vLLM, TensorRT, Ollama), create a new backend class:

```python
from llm_clutch.backend.base import ModelBackend
from llm_clutch.backend.exceptions import (
    ModelLoadError,
    ModelUnloadError,
    BackendError,
)

class VLLMBackend(ModelBackend):
    """Backend implementation for vLLM clusters."""
    
    def __init__(self, base_url: str, timeout_seconds: float = 30):
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
    
    async def load_model(self, model_name: str) -> None:
        """Load model into vLLM."""
        try:
            # Make request to vLLM API
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/v1/models/load",
                    json={"model_name": model_name},
                    timeout=self.timeout_seconds,
                )
                resp.raise_for_status()
        except httpx.HTTPError as e:
            raise ModelLoadError(f"Failed to load {model_name}: {e}") from e
    
    async def unload_model(self) -> None:
        """Unload current model from vLLM."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/v1/models/unload",
                    timeout=self.timeout_seconds,
                )
                resp.raise_for_status()
        except httpx.HTTPError as e:
            raise ModelUnloadError(f"Failed to unload: {e}") from e
    
    async def get_available_memory(self) -> int:
        """Get available GPU memory in bytes."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/v1/gpu_status",
                    timeout=self.timeout_seconds,
                )
                resp.raise_for_status()
                data = resp.json()
                # Adapt based on vLLM's actual response format
                return data.get("available_memory", 0)
        except httpx.HTTPError as e:
            raise BackendError(f"Failed to get memory: {e}") from e
    
    async def get_active_model(self) -> str | None:
        """Get the currently loaded model."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/v1/models",
                    timeout=self.timeout_seconds,
                )
                resp.raise_for_status()
                data = resp.json()
                models = data.get("data", [])
                if models:
                    return models[0].get("id")
                return None
        except httpx.HTTPError as e:
            raise BackendError(f"Failed to get active model: {e}") from e
```

### Best Practices for Custom Backends

1. **Inherit from `ModelBackend`** — Use the abstract interface
2. **Implement all methods** — Python will enforce this at instantiation time
3. **Add retry logic** — Use `tenacity` for transient failures (see `ExoBackend` for example)
4. **Raise appropriate exceptions** — Use `ModelLoadError`, `ModelUnloadError`, `BackendError`
5. **Document assumptions** — What does the backend expect? What endpoints must exist?
6. **Add logging** — Use `structlog` for consistency with the rest of the codebase
7. **Write tests** — Mock the upstream API; test error cases

## Backend Exceptions

All backend exceptions inherit from `BackendError`:

```python
from llm_clutch.backend.exceptions import (
    BackendError,
    ModelLoadError,
    ModelUnloadError,
    InsufficientMemoryError,
)
```

| Exception | Inherits From | When Raised |
| --- | --- | --- |
| `BackendError` | `Exception` | Generic backend error |
| `ModelLoadError` | `BackendError` | Model loading fails |
| `ModelUnloadError` | `BackendError` | Model unloading fails |
| `InsufficientMemoryError` | `BackendError` | Not enough memory for model |

See [Clutch API Reference](clutch.md) for examples of handling these exceptions.
