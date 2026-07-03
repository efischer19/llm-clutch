# Ticket 04: Exo Backend Implementation

**Title:** `feat: [implement Exo backend provider]`

**Labels:** `enhancement`

## What do you want to build?

Create the `ExoBackend` class in `backend/exo.py` — a concrete
implementation of the `ModelBackend` abstract interface (ticket 02) that
communicates with the Exo LLM runner's HTTP API to manage model
lifecycle operations across the cluster.

## Acceptance Criteria

- [ ] `libs/llm-clutch/src/llm_clutch/backend/exo.py` contains an `ExoBackend` class that extends `ModelBackend`
- [ ] `ExoBackend.__init__` accepts the Exo API base URL (e.g., `http://10.0.0.1:52415`) and an optional `httpx.AsyncClient`
- [ ] `load_model()` calls the Exo API to load model weights into the cluster
- [ ] `unload_model()` calls the Exo API to unload the current model
- [ ] `get_available_memory()` queries the Exo topology/health endpoints and returns total available RAM in bytes
- [ ] `get_active_model()` queries Exo for the currently loaded model name
- [ ] All HTTP calls use `httpx.AsyncClient` with configurable timeouts
- [ ] Tenacity retry logic (ADR-010) wraps HTTP calls for transient failures (connection errors, 5xx responses)
- [ ] Custom exceptions from `backend/exceptions.py` are raised on failures (e.g., `ModelLoadError` on load failure)
- [ ] Structured JSON logging (ADR-008) for all API interactions
- [ ] Unit tests use mocked HTTP responses (no real Exo cluster required)
- [ ] `uv run ruff check .` and `uv run pytest` pass

## Implementation Notes

- Use `httpx.AsyncClient` for async HTTP — it is already a project
  dependency from ticket 01.
- The Exo API endpoints will need to be discovered/documented. For this
  ticket, design the implementation around expected endpoint patterns
  (e.g., `/api/v1/models/load`, `/api/v1/topology`). If the exact Exo
  API is not fully documented, create the integration with configurable
  endpoint paths and add `# TODO` markers for verification against a
  live cluster.
- Wrap all `httpx` calls with Tenacity retries: 3 attempts, exponential
  backoff, retry only on `httpx.ConnectError`, `httpx.TimeoutException`,
  and HTTP 5xx responses.
- The `ExoBackend` should be usable as an async context manager
  (`async with ExoBackend(...) as backend:`) to manage the
  `httpx.AsyncClient` lifecycle.
- Consider adding a `health_check()` method (non-abstract, Exo-specific)
  that hits the Exo health endpoint to verify the API is responsive.
