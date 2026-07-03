# Ticket 02: Abstract Backend Provider

**Title:** `feat: [define abstract ModelBackend interface]`

**Labels:** `enhancement`

## What do you want to build?

Create the abstract base class `ModelBackend` in
`backend/base.py` that defines the contract all LLM runner backends must
implement. This interface is the foundation that allows llm-clutch to
support multiple backends (Exo, future runners) without hardcoding to
any specific one.

## Acceptance Criteria

- [ ] `libs/llm-clutch/src/llm_clutch/backend/base.py` contains an abstract base class `ModelBackend` using Python's `abc.ABC`
- [ ] `ModelBackend` defines the following abstract methods with type hints and docstrings:
  - `async def load_model(self, model_name: str) -> None` — load model weights into cluster memory
  - `async def unload_model(self) -> None` — unload the currently active model
  - `async def get_available_memory(self) -> int` — return available unified memory in bytes across the cluster
  - `async def get_active_model(self) -> str | None` — return the name of the currently loaded model, or None
- [ ] A custom exception hierarchy exists in `backend/exceptions.py`: `BackendError`, `ModelLoadError`, `ModelUnloadError`, `InsufficientMemoryError`
- [ ] All methods are async (the Exo API is HTTP-based; async is the natural fit)
- [ ] Unit tests validate that `ModelBackend` cannot be instantiated directly
- [ ] Unit tests validate that a concrete subclass missing any abstract method raises `TypeError`
- [ ] `uv run ruff check .` and `uv run pytest` pass

## Implementation Notes

- Use `abc.ABC` and `abc.abstractmethod` — keep it simple, no metaclass
  tricks.
- All methods should be `async def` since the primary backend (Exo) will
  use HTTP calls via `httpx`.
- The exception hierarchy should inherit from a base `BackendError` that
  itself inherits from `Exception`. This allows callers to catch all
  backend errors with a single handler.
- Consider adding a `backend_name` property (concrete, not abstract) that
  returns `self.__class__.__name__` for logging purposes.
- This ticket does NOT implement any concrete backend — that is ticket 04.
