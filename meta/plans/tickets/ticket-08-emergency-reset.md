# Ticket 08: Emergency Reset Command

**Title:** `feat: [implement emergency reset to known-good single-node state]`

**Labels:** `enhancement`

## What do you want to build?

Add an emergency reset capability that can restore the local cluster to a
known working state (typically a single-node configuration with a
lightweight model) without requiring OpenClaw or any external agent to be
functional. This is the "break glass in case of emergency" feature that
ensures the user can always recover from a bad state.

## Acceptance Criteria

- [ ] `clutch emergency-reset` CLI command exists and is documented
- [ ] The command loads a pre-configured "safe" model on a single specified node (the primary node), bypassing multi-node topology checks
- [ ] The reset sequence: force-unload any active model → verify primary node is reachable → load the safe model on primary node only
- [ ] The safe model name and primary node IP are configurable via config file and CLI flags (e.g., `--safe-model`, `--primary-node`)
- [ ] The command has a `--force` flag that skips confirmation prompts
- [ ] Without `--force`, the command displays the current state and asks for confirmation before proceeding
- [ ] The command works even when the cluster is in an error state (does not depend on multi-node health checks succeeding)
- [ ] Structured logging captures the full reset sequence for debugging
- [ ] A corresponding `async def emergency_reset()` method exists on `LLMClutch` for programmatic access
- [ ] Tests cover: successful reset, reset when cluster is in error state, reset when primary node is unreachable (should fail with clear error)
- [ ] `uv run ruff check .` and `uv run pytest` pass

## Implementation Notes

- The emergency reset is intentionally simpler than `upshift`/`downshift`
  — it targets a single node and skips the full `rev_match` sequence.
  Think of it as the "limp home mode" in a real car.
- The `emergency_reset()` method on `LLMClutch` should accept optional
  overrides for `safe_model` and `primary_node` to allow programmatic
  callers to specify non-default recovery targets.
- The CLI confirmation prompt should clearly show: what model will be
  loaded, which node will be targeted, and warn that all other nodes
  will be left idle.
- Consider making the default safe model and primary node configurable
  in `pyproject.toml` metadata or a dedicated `[tool.llm-clutch]`
  section.
- This feature directly addresses the issue requirement: "allow for
  in-case-of-emergency resets of my local cluster to a known working
  (likely 1-node) state, so I can reset exo without openclaw being
  functional in front of it."
