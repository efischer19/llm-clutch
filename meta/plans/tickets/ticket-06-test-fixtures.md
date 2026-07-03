# Ticket 06: Hardware Mocking & Test Fixtures

**Title:** `feat: [build pytest fixtures for Exo API and network mocking]`

**Labels:** `enhancement`

## What do you want to build?

Create a comprehensive set of pytest fixtures and mock factories that
simulate the Exo API and Thunderbolt network topology, enabling the full
test suite to run without physical hardware. These fixtures should live
in the shared `testing/` directory (per ADR-007) and be reusable across
all llm-clutch tests.

## Acceptance Criteria

- [ ] Shared fixtures exist in `testing/` (or `libs/llm-clutch/tests/conftest.py`) that are importable by all test modules
- [ ] A `mock_exo_backend` fixture provides a `ModelBackend` implementation with configurable behavior (success, failure, latency simulation)
- [ ] A `mock_infra_manager` fixture provides an `InfraManager` with configurable node responses (all up, partial failure, total failure)
- [ ] HTTP-level mocks exist for the Exo API endpoints using `respx` or `pytest-httpx`, simulating: model load success/failure, model unload, topology query, health check
- [ ] Network-level mocks exist for TCP socket checks (simulating reachable/unreachable nodes)
- [ ] A `mock_clutch` fixture composes `mock_exo_backend` + `mock_infra_manager` into a fully testable `LLMClutch` instance
- [ ] Factory functions allow tests to customize mock behavior per test case (e.g., `make_exo_response(status=500)`)
- [ ] All existing tests from tickets 02-05 are refactored to use these shared fixtures (no duplicated mocking code)
- [ ] `uv run pytest` passes with all tests using the new fixtures
- [ ] `uv run ruff check .` passes

## Implementation Notes

- Add `respx` (or `pytest-httpx`) as a development dependency for HTTP
  mocking — it integrates naturally with `httpx`.
- For network mocking, use `unittest.mock.patch` on
  `asyncio.open_connection` to simulate TCP socket behavior without
  hitting real network interfaces.
- Consider using `pytest` parametrize to create matrix tests:
  e.g., test `upshift` with all combinations of node health and API
  response states.
- Fixtures should be designed to be composable — individual tests should
  be able to override specific behaviors without rebuilding the entire
  mock stack.
- The `testing/` shared fixtures should be installable as a path
  dependency or configured via `conftest.py` at the repo root.
- Add `pytest-asyncio` as a dev dependency for async test support.
