# Epic: llm-clutch — Local LLM Cluster Orchestration

## Overview

**llm-clutch** is a hardware-aware, local LLM orchestration package that
safely hot-swaps massive neural networks in memory across a local
multi-node cluster. Using a manual transmission metaphor, it acts as a
"synchromesh" that verifies network topology and available unified memory
before dropping the current model and loading a new one, preventing
cluster crashes.

## Problem Statement

Running a local multi-node AI cluster (e.g., using Exo) presents a
tradeoff between fast daily-driver models and heavyweight reasoning
models. Swapping 75GB+ model weights across standard networks takes 15+
minutes. llm-clutch manages high-speed hot swaps using a centralized
NVMe drive shared over IP-over-Thunderbolt (NFS), with safety checks to
prevent cluster crashes during transitions.

## Goals

When complete, this project will:

1. **Enable reliable model shifting** — up- and down-shift a local exo
   cluster to varying models across varying local topologies
2. **Be useful to the community** — published via PyPI as an open-source
   project meeting high standards for code quality
3. **Support emergency resets** — allow in-case-of-emergency resets to a
   known working (likely 1-node) state, independent of OpenClaw

## Architecture

The codebase uses an abstracted backend provider pattern, with Exo as
the primary v1.0 target:

```text
libs/llm-clutch/
└── src/llm_clutch/
    ├── backend/
    │   ├── base.py          # Abstract ModelBackend interface
    │   └── exo.py           # Exo-specific implementation
    ├── core/
    │   ├── infra.py          # Infrastructure/network health checks
    │   └── clutch.py         # Main LLMClutch orchestrator
    ├── integrations/
    │   └── openclaw.py       # OpenClaw agent tool wrapper
    └── cli.py                # Click-based CLI interface
```

## Key Nomenclature (Transmission Metaphor)

| Term | Function |
| :--- | :--- |
| `rev_match()` | Pre-flight safety check — verify cluster RAM/topology |
| `disengage()` | Unload current model weights from memory |
| `engage()` | Load target model weights into cluster memory |
| `upshift()` | Macro: switch from daily driver → heavy reasoning model |
| `downshift()` | Macro: switch from heavy model → daily driver |

## Proposed ADR

- **ADR-015: Use uv for Dependency Management** — Supersedes ADR-003
  (Poetry). The ecosystem has matured; uv provides 10-100x faster
  dependency resolution, native PEP 621 support, and aligns with the
  Astral tooling ecosystem (Ruff).

## Ticket Sequence

The implementation is broken into 11 sequenced tickets. Dependencies
flow top-to-bottom; tickets at the same level can be parallelized.

```text
┌─────────────────────────────────┐
│  01: Project Scaffolding        │  Foundation — must be first
└──────────────┬──────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌──────────────┐ ┌──────────────┐
│ 02: Abstract │ │ 03: Infra    │  Core interfaces — parallelizable
│   Backend    │ │   Manager    │
└──────┬───────┘ └──────┬───────┘
       │                │
       ▼                │
┌──────────────┐        │
│ 04: Exo      │        │  First concrete backend
│   Backend    │        │
└──────┬───────┘        │
       │                │
       └───────┬────────┘
               ▼
┌─────────────────────────────────┐
│  05: Clutch Engine              │  Main orchestrator — needs 02-04
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  06: Test Fixtures & Mocks      │  Hardware mocking — needs 05
└──────────────┬──────────────────┘
               │
       ┌───────┼───────┐
       ▼       ▼       ▼
┌────────┐ ┌────────┐ ┌────────┐
│ 07:CLI │ │ 08:E-  │ │ 09:    │  User-facing features —
│        │ │ Reset  │ │ OClaw  │  parallelizable
└────┬───┘ └────┬───┘ └────┬───┘
     │          │          │
     └──────────┼──────────┘
                ▼
┌─────────────────────────────────┐
│  10: Documentation              │  Docs — needs user-facing features
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  11: CI/CD & PyPI Publishing    │  Release pipeline — last
└─────────────────────────────────┘
```

## Ticket Index

| # | Title | Dependencies |
| :--- | :--- | :--- |
| 01 | [Project Scaffolding](tickets/ticket-01-project-scaffolding.md) | None |
| 02 | [Abstract Backend Provider](tickets/ticket-02-abstract-backend.md) | 01 |
| 03 | [Infrastructure Manager](tickets/ticket-03-infra-manager.md) | 01 |
| 04 | [Exo Backend Implementation](tickets/ticket-04-exo-backend.md) | 02 |
| 05 | [Clutch Engine Orchestrator](tickets/ticket-05-clutch-engine.md) | 02, 03, 04 |
| 06 | [Hardware Mocking & Test Fixtures](tickets/ticket-06-test-fixtures.md) | 05 |
| 07 | [CLI Interface](tickets/ticket-07-cli.md) | 05, 06 |
| 08 | [Emergency Reset Command](tickets/ticket-08-emergency-reset.md) | 05, 06 |
| 09 | [OpenClaw Tool Integration](tickets/ticket-09-openclaw-integration.md) | 05, 06 |
| 10 | [Documentation & Hardware Guide](tickets/ticket-10-documentation.md) | 07, 08, 09 |
| 11 | [CI/CD & PyPI Publishing](tickets/ticket-11-cicd-publishing.md) | 10 |

## Relevant ADRs

| ADR | Title | Relevance |
| :--- | :--- | :--- |
| ADR-003 | Use Poetry | **Superseded** by proposed ADR-015 (uv) |
| ADR-004 | Use pytest | Testing framework for all tickets |
| ADR-005 | Use Ruff | Linting/formatting for all code |
| ADR-007 | Monorepo /apps structure | Library lives in `libs/` |
| ADR-008 | JSON Structured Logging | Logging in core modules |
| ADR-010 | Use Tenacity | Retry logic for network/API calls |
| ADR-011 | Use Click | CLI framework for tickets 07, 08 |
| ADR-014 | CI/CD Strategy | Basis for ticket 11 |
| ADR-015 | Use uv (Proposed) | Replaces Poetry across all tickets |
