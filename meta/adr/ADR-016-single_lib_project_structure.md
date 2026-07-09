---
title: "ADR-016: Single-Lib Project Structure"
status: "Accepted"
date: "2026-07-09"
supersedes: "ADR-007"
tags:
  - "architecture"
  - "project-structure"
  - "monorepo"
---

## Context

* **Problem:** ADR-007 established a monorepo structure with `/apps` and `/libs`
  directories to support multiple applications and shared libraries. However,
  the project has evolved to focus on a single library (`llm-clutch`) as its
  only effective artifact. The multi-project structure adds unnecessary
  complexity and maintenance burden.
* **Constraints:** The project must maintain clear organization with source
  code, tests, and documentation. The build and deployment process (using `uv`
  and PyPI publishing) should remain streamlined.

## Decision

We will restructure the repository to reflect its single-library focus by
promoting `libs/llm-clutch` to the repository root. The new structure is:

```text
├── src/                    # Python package source (llm_clutch)
├── tests/                  # Test files
├── pyproject.toml          # Project metadata and dependencies
├── uv.lock                 # Dependency lock file
├── README.md               # Project overview and quick start
├── meta/                   # ADRs and project planning
├── .github/                # GitHub Actions workflows
├── docs-src/               # Documentation source files
├── testing/                # Shared test utilities
└── scripts/                # Automation and utility scripts
```

### Structure Details

* **`src/llm_clutch/`**: The main Python package containing all library code
* **`tests/`**: Unit and integration tests for the library
* **`pyproject.toml`**: Project metadata, dependencies, and build configuration
* **`uv.lock`**: Pinned dependency versions for reproducible builds
* **`meta/adr/`**: Architecture Decision Records documenting design choices
* **`.github/workflows/`**: CI/CD pipeline definitions

### Removed Elements

* `apps/` directory (template application structure no longer needed)
* `libs/` directory hierarchy (promoted to root)
* `templates/python-app-template/` and `templates/python-lib-template/`
  (template scaffolding for multiple projects)

## Considered Options

1. **Single-library at root (Chosen):** Promote `libs/llm-clutch` to the
   repository root.
   * *Pros:* Clear, simplified structure. Reduces cognitive overhead. Direct
     repository-level build and test commands. Easier to find code and
     documentation.
   * *Cons:* Cannot easily expand to multiple applications in the future
     without restructuring again.

2. **Keep monorepo structure:** Maintain `/apps` and `/libs` for potential
   future growth.
   * *Pros:* Flexible for adding more projects later.
   * *Cons:* Unnecessary complexity for current single-library project.
     Requires running tests for multiple (mostly empty) projects in CI.

3. **Flat structure at root:** Place all files directly in root without `/src`
   and `/tests` subdirectories.
   * *Pros:* Maximum simplicity.
   * *Cons:* Does not follow Python packaging standards. Harder to maintain
     as project grows.

## Consequences

* **Positive:** Significantly simplified repository structure. All tooling
  commands (`uv run pytest`, `uv build`, etc.) operate directly from the
  repository root. Clearer navigation for new contributors. CI/CD pipelines
  become more straightforward.
* **Negative:** Less flexible for future expansion. Any future applications or
  libraries would require restructuring the repository again.
* **Future Implications:** If the project grows to include multiple libraries
  or applications, this decision may need to be revisited and a new ADR
  created to re-establish a monorepo structure.

## Migration Path

1. Copy contents of `libs/llm-clutch/` to repository root
2. Remove `apps/` and `libs/` directories
3. Remove unused template directories
4. Update CI/CD workflows to reference root-level paths
5. Update documentation and internal links
6. Mark ADR-007 as `Superseded` by this ADR
