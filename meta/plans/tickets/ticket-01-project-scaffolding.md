# Ticket 01: Project Scaffolding

**Title:** `feat: [scaffold llm-clutch library with uv and project structure]`

**Labels:** `enhancement`

## What do you want to build?

Set up the llm-clutch library under `libs/llm-clutch/` following the
monorepo structure defined in ADR-007. Initialize the project with uv
(per proposed ADR-015), configure Ruff linting (ADR-005), and establish
the package directory layout that all subsequent tickets will build upon.

## Acceptance Criteria

- [ ] `libs/llm-clutch/pyproject.toml` exists with valid PEP 621 metadata (name: `llm-clutch`, Python >=3.12)
- [ ] Package source directory exists at `libs/llm-clutch/src/llm_clutch/` with an `__init__.py` exposing the package version
- [ ] Sub-package directories exist: `backend/`, `core/`, `integrations/` (each with `__init__.py`)
- [ ] `libs/llm-clutch/tests/` directory exists with a passing placeholder test
- [ ] `uv sync` completes successfully and creates a working `.venv`
- [ ] `uv run ruff check .` passes with zero violations
- [ ] `uv run ruff format --check .` passes with zero violations
- [ ] `uv run pytest` runs successfully with the placeholder test passing
- [ ] A `libs/llm-clutch/README.md` exists with a brief project description

## Implementation Notes

- Follow the monorepo conventions from ADR-007 — the library lives under
  `libs/`, not `apps/`, since it is a reusable package (not a deployable
  application).
- Use `uv init --lib` or manually create `pyproject.toml` with PEP 621
  metadata. Do not use Poetry.
- Configure Ruff in `pyproject.toml` per ADR-005 conventions.
- Add development dependencies: `pytest`, `ruff`, `mypy`.
- Add runtime dependencies: `click`, `tenacity`, `httpx` (for async HTTP
  to Exo API), `structlog` (for JSON logging per ADR-008).
- Remove or update the `example-lib/` template if it is no longer needed.
- Reference ADR-015 (uv) in the PR description.
