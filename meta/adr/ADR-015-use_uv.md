---
title: "ADR-015: Use uv for Dependency Management"
status: "Proposed"
date: "2026-07-03"
supersedes: "ADR-003"
tags:
  - "python"
  - "dependencies"
  - "core-tooling"
---

## Context

- **Problem:** ADR-003 selected Poetry for dependency management. Since
  that decision, the Python packaging ecosystem has matured significantly.
  `uv` (by Astral, the creators of Ruff) has evolved from an experimental
  pip replacement into a full-featured project manager with lock file
  support, virtual environment management, and `pyproject.toml`-native
  workflows. Given that this project is greenfield, now is the ideal time
  to adopt the faster, simpler tool before any Poetry lock files or
  workflows are established.
- **Constraints:** The tool must support monorepo workflows (per ADR-007),
  produce reproducible builds, integrate with CI/CD pipelines (ADR-014),
  and work alongside Ruff (ADR-005) without conflict. It must support
  publishing to PyPI.

## Decision

We will use **[uv](https://docs.astral.sh/uv/)** for dependency
management across all Python applications and libraries in this project,
superseding ADR-003 (Poetry).

Each application in `apps/` and each library in `libs/` will have its own
`pyproject.toml` managed by uv. This provides:

- **Deterministic dependency resolution** via `uv.lock` files.
- **Standardized project metadata** in `pyproject.toml` (PEP 621
  compliant).
- **Virtual environment management** — uv creates and manages isolated
  `.venv` environments per project.
- **Build and publish support** — `uv build` and `uv publish` handle the
  full package lifecycle.
- **Extreme speed** — dependency resolution and installation are
  10-100x faster than Poetry due to uv's Rust implementation.

### Key Conventions

- Applications **commit** their `uv.lock` files for reproducible
  deployments.
- Libraries **may** choose to exclude `uv.lock` from version control
  to test against the latest compatible versions.
- Use `uv sync` to install dependencies into the project's `.venv`.
- Use `uv run <command>` to execute commands within the virtual
  environment (e.g., `uv run pytest`, `uv run ruff check .`).

## Considered Options

1. **uv (Chosen):** Ultra-fast Rust-based Python package and project
   manager by Astral.
    - *Pros:* 10-100x faster than Poetry, native `pyproject.toml` support
      (PEP 621), built-in lock files, virtual environment management,
      pip-compatible, same vendor as Ruff (consistent tooling ecosystem),
      single binary install, excellent monorepo support.
    - *Cons:* Younger project than Poetry, though now stable and
      widely adopted. Some advanced Poetry features (e.g., plugin system)
      have no direct equivalent.
2. **Poetry (Previous choice, ADR-003):** Modern dependency management
   with lock files and `pyproject.toml` support.
    - *Pros:* Mature ecosystem, large community, strong documentation.
    - *Cons:* Slower dependency resolution, heavier installation footprint,
      custom metadata format (not fully PEP 621), separate tool from
      the linting ecosystem.
3. **pip + requirements.txt:** The traditional Python approach.
    - *Pros:* Zero additional tooling, universally understood.
    - *Cons:* No lock file by default, manual virtual environment
      management, no dependency resolution guarantees.

## Consequences

- **Positive:** Faster CI/CD pipelines due to dramatically reduced
  dependency resolution time. Consistent Astral tooling ecosystem
  (uv + Ruff). Simpler installation (single binary). Native PEP 621
  compliance means `pyproject.toml` is portable across tools.
- **Negative:** Contributors familiar with Poetry will need to learn uv
  commands. CI workflows (ADR-014) must be updated to use uv instead of
  Poetry. The composite action `setup-python-poetry` will need to be
  replaced with a uv-based equivalent.
- **Future Implications:** Aligning on Astral tooling (uv for packaging,
  Ruff for linting) creates a cohesive, high-performance development
  experience. Docker build stages (ADR-006) should be updated to use
  `uv sync` instead of `poetry export`.
