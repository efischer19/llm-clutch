# Ticket 10: Documentation & Hardware Guide

**Title:** `feat: [write project documentation, README, and hardware guide]`

**Labels:** `enhancement`

## What do you want to build?

Create comprehensive documentation for llm-clutch including: a
user-facing README, a hardware setup guide (based on the existing seed
doc), API reference documentation, and MkDocs site configuration (per
ADR-012) for publishing to GitHub Pages.

## Acceptance Criteria

- [ ] `README.md` is updated with: project overview, quick-start installation (`pip install llm-clutch`), basic usage examples (Python API and CLI), link to full docs
- [ ] A `HARDWARE_GUIDE.md` exists in `docs-src/` covering the Thunderbolt/NFS setup, adapted from the existing seed hardware guide in `meta/plans/seed_docs/`
- [ ] The hardware guide clearly states this setup is recommended but not required for the package to function
- [ ] API reference docs exist for all public classes: `LLMClutch`, `ModelBackend`, `ExoBackend`, `InfraManager`
- [ ] CLI usage documentation covers all commands with examples
- [ ] `mkdocs.yml` is updated (or a new nav section added) to include llm-clutch docs
- [ ] `mkdocs build --strict` passes
- [ ] Configuration file format is documented (YAML/TOML config structure, environment variables)
- [ ] A "Contributing" section explains how to set up the dev environment with uv and run tests

## Implementation Notes

- The hardware guide in `meta/plans/seed_docs/` is written for a specific
  3-node Mac cluster. Adapt it into a more general guide that uses that
  setup as a concrete example but explains the principles (Thunderbolt
  bridging, NFS for fast model access) so users with different hardware
  can adapt.
- For API reference, consider using `mkdocstrings` to auto-generate docs
  from docstrings. Add it to `docs-requirements.txt` if used.
- The README should include a "Why llm-clutch?" section that explains the
  transmission metaphor and the problem it solves (elevator pitch from
  the seed doc).
- Include a "Supported Backends" section that lists Exo as the v1.0
  backend and explains how to implement a custom backend.
- Keep the quick-start example minimal — 5-10 lines of Python showing
  an upshift/downshift cycle.
