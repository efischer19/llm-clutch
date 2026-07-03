# Ticket 07: CLI Interface

**Title:** `feat: [implement Click CLI for llm-clutch operations]`

**Labels:** `enhancement`

## What do you want to build?

Create a Click-based CLI (per ADR-011) that exposes all llm-clutch
operations as command-line commands. This CLI is the primary human
interface for managing model shifts, checking cluster status, and
running diagnostics.

## Acceptance Criteria

- [ ] `libs/llm-clutch/src/llm_clutch/cli.py` contains a Click command group `clutch`
- [ ] `clutch status` — displays current cluster state: active model, node health, available memory
- [ ] `clutch upshift --model <name> --ram <bytes>` — triggers an upshift to the specified model
- [ ] `clutch downshift --model <name> --ram <bytes>` — triggers a downshift to the specified model
- [ ] `clutch check` — runs a topology health check and displays node status table
- [ ] All commands support `--config <path>` for specifying a configuration file (node IPs, Exo API URL, default models)
- [ ] All commands provide clear `--help` documentation
- [ ] Output is human-readable by default, with a `--json` flag for machine-parseable output
- [ ] Error states produce clear, actionable error messages (not raw tracebacks)
- [ ] A `pyproject.toml` `[project.scripts]` entry point registers `clutch` as a CLI command
- [ ] Tests use `click.testing.CliRunner` (per ADR-011) to validate all commands
- [ ] `uv run ruff check .` and `uv run pytest` pass

## Implementation Notes

- Follow the patterns in ADR-011 exactly — use decorator-based commands,
  `CliRunner` for tests.
- Since the core API is async but Click is synchronous, use
  `asyncio.run()` in the CLI layer to bridge the sync/async boundary.
  Keep async logic in the core; the CLI is a thin synchronous wrapper.
- For configuration, support a YAML or TOML file at a default path
  (e.g., `~/.config/llm-clutch/config.toml`) with CLI flags overriding
  file values.
- The `--json` flag should output structured JSON matching the
  `NodeStatus` and `ClutchStatus` dataclass shapes for scripting use.
- Consider using `click.echo` with `rich` or plain formatting for the
  status table. Keep it simple for v1 — a formatted text table is fine.
