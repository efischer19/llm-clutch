# Ticket 05: Clutch Engine Orchestrator

**Title:** `feat: [implement LLMClutch engine with upshift/downshift orchestration]`

**Labels:** `enhancement`

## What do you want to build?

Create the `LLMClutch` class in `core/clutch.py` — the main orchestrator
that ties the `InfraManager` and `ModelBackend` together, exposing the
transmission-metaphor API (`rev_match`, `disengage`, `engage`, `upshift`,
`downshift`) to end users and agents.

## Acceptance Criteria

- [ ] `libs/llm-clutch/src/llm_clutch/core/clutch.py` contains the `LLMClutch` class
- [ ] `LLMClutch.__init__` accepts a `ModelBackend` instance, an `InfraManager` instance, and optional configuration (min_nodes, default models)
- [ ] Implements `async def rev_match(self, required_ram: int) -> bool` — checks topology and available memory, returns True if the cluster can accept a model of the given size
- [ ] Implements `async def disengage(self) -> None` — calls `backend.unload_model()` with safety checks
- [ ] Implements `async def engage(self, model_name: str) -> None` — calls `backend.load_model()` with pre-flight validation
- [ ] Implements `async def upshift(self, heavy_model: str, required_ram: int) -> None` — orchestrates `rev_match()` → `disengage()` → `engage()` for moving to a heavy model
- [ ] Implements `async def downshift(self, light_model: str, required_ram: int) -> None` — orchestrates the reverse (back to daily driver)
- [ ] `upshift` and `downshift` are atomic: if any step fails, the system logs the failure state and does not leave the cluster in a partially loaded state
- [ ] Structured logging (ADR-008) at each stage of the shift process
- [ ] A `status()` method returns the current state: active model, cluster health, last shift result
- [ ] Unit tests cover: successful upshift, successful downshift, rev_match failure (insufficient RAM), rev_match failure (nodes unreachable), disengage failure, engage failure
- [ ] `uv run ruff check .` and `uv run pytest` pass

## Implementation Notes

- The `LLMClutch` class is the primary public API of the package. It
  should be importable directly from `llm_clutch`:
  `from llm_clutch import LLMClutch`.
- Use dependency injection — accept `ModelBackend` and `InfraManager` in
  the constructor rather than creating them internally. This makes
  testing straightforward and supports different backend implementations.
- The `upshift`/`downshift` methods should be functionally identical
  except for logging context (the names exist for semantic clarity in
  agent workflows).
- Error handling strategy: if `rev_match` fails, raise immediately
  (no model was disturbed). If `disengage` succeeds but `engage` fails,
  log a CRITICAL error — the cluster is now model-less. Consider adding
  a `recovery_model` parameter to attempt loading a fallback.
- Consider a simple state enum: `IDLE`, `SHIFTING`, `ENGAGED`, `ERROR`
  to track the engine's lifecycle.
