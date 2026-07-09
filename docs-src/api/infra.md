# API Reference: Infrastructure Manager

The `InfraManager` class is responsible for cluster health checks. It verifies that worker nodes are reachable before any model shift is attempted, preventing shifts into a degraded cluster.

## InfraManager

Manager for cluster infrastructure health checks using TCP socket probes.

### Class Definition

```python
from llm_clutch.core.infra import InfraManager

infra = InfraManager(node_ips=["10.0.0.1", "10.0.0.2", "10.0.0.3"])
```

### Constructor

```python
def __init__(
    self,
    node_ips: list[str],
    timeout_seconds: float = 5,
    port: int = 52415,
) -> None:
```

**Parameters:**

- `node_ips` (`list[str]`) — List of target node IP addresses to monitor (e.g., `["10.0.0.1", "10.0.0.2"]`)
- `timeout_seconds` (`float`, optional) — Timeout in seconds for each node health check. Defaults to 5
- `port` (`int`, optional) — TCP port to probe on each node. Defaults to 52415 (Exo API port)

**Example:**

```python
infra = InfraManager(
    node_ips=["10.0.0.1", "10.0.0.2", "10.0.0.3"],
    timeout_seconds=3,  # Quick timeout for responsive cluster
    port=52415  # Exo API port
)
```

### Attributes

- `node_ips` (`list[str]`) — The list of node IPs being monitored
- `timeout_seconds` (`float`) — Timeout for each check
- `port` (`int`) — Port being probed
- `DEFAULT_TIMEOUT_SECONDS` (`int`) — Class constant set to 5
- `DEFAULT_PORT` (`int`) — Class constant set to 52415 (Exo API port)

### Methods

#### `check_node(ip: str) -> NodeStatus` *(async)*

Check if a single node is reachable via TCP socket probe.

Attempts to establish a TCP connection to the specified IP and port. Includes automatic retry logic with exponential backoff on transient network failures. Returns a `NodeStatus` regardless of success or failure.

```python
async def check_node(self, ip: str) -> NodeStatus:
```

**Parameters:**

- `ip` (`str`) — IP address of the node to check

**Returns:**

`NodeStatus` object containing:
- `ip` — The node's IP address
- `reachable` — Boolean indicating if the node responded
- `latency_ms` — Response time in milliseconds (or `None` if unreachable)
- `checked_at` — Timestamp when the check was performed

**Example:**

```python
status = await infra.check_node("10.0.0.1")
print(f"Node reachable: {status.reachable}")
if status.reachable:
    print(f"Latency: {status.latency_ms:.1f} ms")
```

#### `check_all_nodes() -> list[NodeStatus]` *(async)*

Check all configured nodes in parallel and return their statuses.

```python
async def check_all_nodes(self) -> list[NodeStatus]:
```

**Returns:**

List of `NodeStatus` objects, one per node, in the same order as `self.node_ips`

**Example:**

```python
statuses = await infra.check_all_nodes()
for status in statuses:
    health = "✓" if status.reachable else "✗"
    latency = f"{status.latency_ms:.1f} ms" if status.reachable else "—"
    print(f"{health} {status.ip} ({latency})")

# Example output:
# ✓ 10.0.0.1 (0.5 ms)
# ✓ 10.0.0.2 (1.2 ms)
# ✓ 10.0.0.3 (0.8 ms)
```

#### `is_healthy(min_reachable: int) -> bool` *(async)*

Check if the cluster is healthy (at least `min_reachable` nodes are reachable).

```python
async def is_healthy(self, min_reachable: int) -> bool:
```

**Parameters:**

- `min_reachable` (`int`) — Minimum number of nodes that must be reachable

**Returns:**

`bool` — `True` if at least `min_reachable` nodes are reachable, `False` otherwise

**Example:**

```python
healthy = await infra.is_healthy(min_reachable=2)
if healthy:
    print("Cluster is healthy (at least 2 nodes reachable)")
else:
    print("Cluster is degraded!")
```

#### `get_healthy_nodes() -> list[str]` *(async)*

Get a list of currently reachable node IP addresses.

```python
async def get_healthy_nodes(self) -> list[str]:
```

**Returns:**

List of IP addresses that are currently reachable

**Example:**

```python
healthy = await infra.get_healthy_nodes()
print(f"Healthy nodes: {', '.join(healthy)}")
# Output: Healthy nodes: 10.0.0.1, 10.0.0.3
```

## NodeStatus

Dataclass containing the result of a single node health check.

### Fields

```python
@dataclass
class NodeStatus:
    ip: str
    reachable: bool
    latency_ms: float | None
    checked_at: datetime
```

**Attributes:**

- `ip` (`str`) — IP address of the node
- `reachable` (`bool`) — Whether the node responded to the health check
- `latency_ms` (`float | None`) — Response time in milliseconds, or `None` if unreachable
- `checked_at` (`datetime`) — When the check was performed (UTC)

**Example:**

```python
import json
from dataclasses import asdict

status = await infra.check_node("10.0.0.1")
print(json.dumps(asdict(status), default=str, indent=2))
# Output:
# {
#   "ip": "10.0.0.1",
#   "reachable": true,
#   "latency_ms": 0.5,
#   "checked_at": "2026-07-09T11:54:00+00:00"
# }
```

## Retry Behavior

InfraManager automatically retries failed node checks with exponential backoff:

- **Max attempts:** 3
- **Initial wait:** 1 second
- **Max wait:** 10 seconds
- **Retried on:** `OSError`, `TimeoutError`

This ensures temporary network glitches don't immediately mark nodes as unhealthy.

## Common Patterns

### Check Cluster Health Before Shifts

```python
async def safe_upshift(clutch, heavy_model, required_ram):
    # Check cluster health first
    healthy = await clutch.infra_manager.is_healthy(min_reachable=2)
    if not healthy:
        print("Cluster is degraded—cannot upshift")
        return False
    
    # Proceed with upshift
    result = await clutch.upshift(heavy_model, required_ram)
    return result.success
```

### Monitor Cluster Continuously

```python
import asyncio

async def monitor_cluster():
    infra = InfraManager(node_ips=["10.0.0.1", "10.0.0.2", "10.0.0.3"])
    
    while True:
        statuses = await infra.check_all_nodes()
        
        for status in statuses:
            if status.reachable:
                print(f"✓ {status.ip} ({status.latency_ms:.1f} ms)")
            else:
                print(f"✗ {status.ip} (unreachable)")
        
        # Check every 30 seconds
        await asyncio.sleep(30)

# Run monitoring
# asyncio.run(monitor_cluster())
```

### List Healthy Nodes After Degradation

```python
async def get_degraded_nodes():
    infra = InfraManager(node_ips=["10.0.0.1", "10.0.0.2", "10.0.0.3"])
    
    statuses = await infra.check_all_nodes()
    healthy = [s.ip for s in statuses if s.reachable]
    unhealthy = [s.ip for s in statuses if not s.reachable]
    
    if unhealthy:
        print(f"Warning: {len(unhealthy)} node(s) unreachable: {', '.join(unhealthy)}")
    
    return healthy
```

### Detect Latency Issues

```python
async def detect_latency_issues(threshold_ms=5.0):
    infra = InfraManager(node_ips=["10.0.0.1", "10.0.0.2", "10.0.0.3"])
    
    statuses = await infra.check_all_nodes()
    
    high_latency = [
        s for s in statuses 
        if s.reachable and s.latency_ms and s.latency_ms > threshold_ms
    ]
    
    if high_latency:
        print(f"High latency detected:")
        for s in high_latency:
            print(f"  {s.ip}: {s.latency_ms:.1f} ms")
    
    return len(high_latency) == 0
```

## Troubleshooting

| Problem | Likely Cause | Solution |
| --- | --- | --- |
| **All nodes show unreachable** | Network configuration or firewall | Check node IPs are correct; verify nodes are on the correct subnet; check firewall rules |
| **Some nodes intermittently unreachable** | Network instability or node overload | Check network cables/connections; reduce cluster load; increase `timeout_seconds` |
| **Latency is very high (>100 ms)** | Network congestion or distance | Use dedicated network for cluster communication; check for interference; verify network bandwidth |
| **InfraManager never returns** | All nodes are down or wrong port | Verify cluster is running; check port number matches Exo API port; increase `timeout_seconds` |

## Integration with LLMClutch

The `LLMClutch` class uses `InfraManager` to enforce minimum cluster health before allowing model shifts:

```python
clutch = LLMClutch(
    backend=backend,
    infra_manager=infra,
    min_nodes=2  # Require at least 2 nodes for shifts
)

# Before each shift, LLMClutch calls:
healthy = await infra.is_healthy(min_reachable=2)
if not healthy:
    raise ValueError("Cluster is not healthy enough for shifts")
```

See [LLMClutch API Reference](clutch.md) for details on how health checks integrate with shift operations.
