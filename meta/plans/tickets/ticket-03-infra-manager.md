# Ticket 03: Infrastructure Manager

**Title:** `feat: [implement infrastructure manager for node health checks]`

**Labels:** `enhancement`

## What do you want to build?

Create the `InfraManager` class in `core/infra.py` that handles
hardware-level health checks for the cluster nodes. This module verifies
that worker nodes on the Thunderbolt subnet are reachable before any
model shift is attempted, preventing shifts into a degraded cluster.

## Acceptance Criteria

- [ ] `libs/llm-clutch/src/llm_clutch/core/infra.py` contains an `InfraManager` class
- [ ] `InfraManager` accepts a configuration of target node IPs (e.g., `["10.0.0.1", "10.0.0.2", "10.0.0.3"]`)
- [ ] Implements `async def check_node(self, ip: str) -> NodeStatus` — checks if a single node is reachable via TCP socket probe
- [ ] Implements `async def check_all_nodes(self) -> list[NodeStatus]` — checks all configured nodes concurrently using `asyncio.gather`
- [ ] Implements `async def verify_topology(self, min_nodes: int = 1) -> bool` — returns True only if at least `min_nodes` are reachable
- [ ] `NodeStatus` is a dataclass or Pydantic model with fields: `ip`, `reachable` (bool), `latency_ms` (float | None), `checked_at` (datetime)
- [ ] Uses structured logging (ADR-008) to log node check results
- [ ] Uses Tenacity (ADR-010) for retry logic on node checks (transient network failures)
- [ ] Unit tests cover: all nodes reachable, partial failure, total failure, timeout scenarios
- [ ] `uv run ruff check .` and `uv run pytest` pass

## Implementation Notes

- Use `asyncio.open_connection` for TCP socket probes rather than ICMP
  ping, since ICMP often requires root privileges. Probe a known port
  (e.g., the Exo API port) or simply attempt a TCP connect to validate
  reachability.
- Node checks should run concurrently with `asyncio.gather` and have
  configurable timeouts (default 5 seconds per node).
- The configuration should be loadable from a YAML/TOML config file or
  environment variables — but for this ticket, accepting a list of IPs
  in the constructor is sufficient. Config file loading can be a
  follow-up.
- Tenacity retries should use exponential backoff with a maximum of 3
  attempts per node.
- Log each node check result at INFO level, failures at WARNING.
