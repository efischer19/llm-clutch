# CLI Reference

The llm-clutch command-line interface provides commands for managing model shifts, checking cluster health, and emergency recovery.

## Overview

```bash
# Display help
clutch --help

# Load a custom config file
clutch --config /path/to/config.toml status

# Most commands support both human-readable and JSON output
clutch status              # Human-readable
clutch status --json       # Machine-parseable JSON
```

## Global Options

### `--config` / `-c`

Path to a configuration file (TOML format). If not provided, defaults to `~/.config/llm-clutch/config.toml`.

```bash
clutch --config /etc/llm-clutch/production.toml status
clutch -c ./dev.toml upshift --model GPT-OSS-120B --ram 75000000000
```

## Commands

### `clutch status`

Display the current state of the cluster: active model, node health, and last shift result.

**Usage:**

```bash
clutch status [OPTIONS]
```

**Options:**

- `--json` — Output as JSON for machine parsing

**Examples:**

```bash
# Human-readable output
$ clutch status
Engine State: idle
Active Model: Qwen3-Next-80B
Cluster Health: Healthy
Last Shift: ✓ Success
  Previous: GPT-OSS-120B
  New: Qwen3-Next-80B

# JSON output (for scripts, monitoring)
$ clutch status --json
{
  "state": "idle",
  "active_model": "Qwen3-Next-80B",
  "cluster_health": true,
  "last_shift_result": {
    "success": true,
    "previous_model": "GPT-OSS-120B",
    "new_model": "Qwen3-Next-80B",
    "error": null,
    "timestamp": "2026-07-09T12:30:00+00:00"
  }
}
```

**Exit Codes:**

- `0` — Success
- `1` — Configuration error or backend error

---

### `clutch upshift`

Trigger an upshift to a heavier model for intensive reasoning tasks.

Performs a safe atomic shift: pre-flight check (`rev_match`) → disengage current model → engage new model. If any step fails, the operation fails with clear error messaging.

**Usage:**

```bash
clutch upshift --model MODEL_NAME --ram REQUIRED_RAM_BYTES [OPTIONS]
```

**Required Arguments:**

- `--model MODEL_NAME` — Name of the heavy model to load (e.g., `"GPT-OSS-120B"`)
- `--ram REQUIRED_RAM_BYTES` — Required RAM in bytes for the model (e.g., `75000000000` for 75 GB)

**Options:**

- `--json` — Output as JSON for machine parsing

**Examples:**

```bash
# Upshift to GPT-OSS-120B (75 GB)
$ clutch upshift --model "GPT-OSS-120B" --ram 75000000000
✓ Successfully upshifted to GPT-OSS-120B
  Active model: GPT-OSS-120B

# With JSON output (for automation)
$ clutch upshift --model "GPT-OSS-120B" --ram 75000000000 --json
{
  "success": true,
  "model": "GPT-OSS-120B",
  "active_model": "GPT-OSS-120B",
  "error": null
}

# Failed upshift (cluster unhealthy)
$ clutch upshift --model "GPT-OSS-120B" --ram 75000000000
Error: Cluster is not healthy enough for shifts
```

**Pre-flight Checks:**

Before upshifting, the system verifies:

1. Cluster is reachable (at least the minimum number of nodes)
2. Cluster has enough available memory
3. Current model can be unloaded

**Failure Scenarios:**

| Error | Cause | Solution |
| --- | --- | --- |
| `No node IPs configured` | Configuration incomplete | Set `node_ips` in config file |
| `Cluster is not healthy` | One or more nodes unreachable | Run `clutch check` to diagnose |
| `Insufficient memory` | Not enough RAM for the model | Ensure models are not oversized; check cluster memory capacity |
| `Failed to unload` | Current model won't unload | Use `clutch emergency-reset` to force-unload |

**Exit Codes:**

- `0` — Upshift succeeded
- `1` — Upshift failed (configuration, cluster, or backend error)

---

### `clutch downshift`

Trigger a downshift to a lighter daily-driver model.

Performs a safe atomic shift: pre-flight check → disengage current model → engage new model. Identical process to upshift, but typically transitions from a heavy reasoning model back to a fast, efficient model.

**Usage:**

```bash
clutch downshift --model MODEL_NAME --ram REQUIRED_RAM_BYTES [OPTIONS]
```

**Required Arguments:**

- `--model MODEL_NAME` — Name of the light model to load (e.g., `"Qwen3-Next-80B"`)
- `--ram REQUIRED_RAM_BYTES` — Required RAM in bytes for the model (e.g., `50000000000` for 50 GB)

**Options:**

- `--json` — Output as JSON for machine parsing

**Examples:**

```bash
# Downshift to Qwen3-Next-80B (50 GB)
$ clutch downshift --model "Qwen3-Next-80B" --ram 50000000000
✓ Successfully downshifted to Qwen3-Next-80B
  Active model: Qwen3-Next-80B

# With JSON output (for automation)
$ clutch downshift --model "Qwen3-Next-80B" --ram 50000000000 --json
{
  "success": true,
  "model": "Qwen3-Next-80B",
  "active_model": "Qwen3-Next-80B",
  "error": null
}
```

**Typical Workflow:**

```bash
# 1. Start with fast daily driver
$ clutch status
Active Model: Qwen3-Next-80B

# 2. Agent detects complex task, requests upshift
$ clutch upshift --model "GPT-OSS-120B" --ram 75000000000

# 3. Agent completes reasoning task
# 4. Agent requests downshift
$ clutch downshift --model "Qwen3-Next-80B" --ram 50000000000

# 5. Back to fast daily operations
$ clutch status
Active Model: Qwen3-Next-80B
```

---

### `clutch check`

Run a topology health check and display the status of all configured nodes.

Probes each node via TCP socket connection to verify reachability and measure latency. Returns a formatted table or JSON report.

**Usage:**

```bash
clutch check [OPTIONS]
```

**Options:**

- `--json` — Output as JSON for machine parsing

**Examples:**

```bash
# Human-readable table output
$ clutch check
======================================================================
Cluster Topology Health Check
======================================================================
IP Address           Status          Latency (ms)    Checked
----------------------------------------------------------------------
10.0.0.1             ✓ Reachable     0.50            2026-07-09 12:30:15
10.0.0.2             ✓ Reachable     1.20            2026-07-09 12:30:15
10.0.0.3             ✓ Reachable     0.85            2026-07-09 12:30:15
======================================================================
Summary: 3/3 nodes reachable

# JSON output (for monitoring/alerting systems)
$ clutch check --json
[
  {
    "ip": "10.0.0.1",
    "reachable": true,
    "latency_ms": 0.50,
    "checked_at": "2026-07-09T12:30:15+00:00"
  },
  {
    "ip": "10.0.0.2",
    "reachable": true,
    "latency_ms": 1.20,
    "checked_at": "2026-07-09T12:30:15+00:00"
  },
  {
    "ip": "10.0.0.3",
    "reachable": true,
    "latency_ms": 0.85,
    "checked_at": "2026-07-09T12:30:15+00:00"
  }
]

# Degraded cluster (one node down)
$ clutch check
======================================================================
Cluster Topology Health Check
======================================================================
IP Address           Status          Latency (ms)    Checked
----------------------------------------------------------------------
10.0.0.1             ✓ Reachable     0.50            2026-07-09 12:30:15
10.0.0.2             ✗ Unreachable   N/A             2026-07-09 12:30:15
10.0.0.3             ✓ Reachable     0.85            2026-07-09 12:30:15
======================================================================
Summary: 2/3 nodes reachable
```

**Interpreting Results:**

| Result | Interpretation | Action |
| --- | --- | --- |
| All ✓ Reachable | Cluster is healthy | Proceed with shifts |
| Some ✗ Unreachable | Cluster is degraded | Check network, reboot nodes, or `emergency-reset` |
| All ✗ Unreachable | Cluster is down | Check network connection, power, Exo service |
| High latency (>10ms) | Network is congested | Investigate network, check for interference |

---

### `clutch emergency-reset`

Perform an emergency reset to restore the cluster to a known working state.

This is the "break glass in case of emergency" command that bypasses pre-flight checks and force-unloads any active model, then loads a safe fallback model on the primary node. Use only when the cluster is stuck or hung.

**Usage:**

```bash
clutch emergency-reset [OPTIONS]
```

**Options:**

- `--safe-model MODEL_NAME` — Name of the safe fallback model (e.g., `"llama-7b"`). Can be configured in config file.
- `--primary-node IP_ADDRESS` — IP address of the primary node to target (e.g., `"10.0.0.1"`). Can be configured in config file; defaults to first node in config.
- `--force` — Skip confirmation prompt and proceed with reset
- `--json` — Output as JSON for machine parsing

**Configuration (Optional):**

You can configure defaults in your `~/.config/llm-clutch/config.toml`:

```toml
[llm_clutch]
node_ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
exo_api_url = "http://10.0.0.1:52415"

# Emergency reset defaults
safe_model = "llama-7b"
primary_node = "10.0.0.1"
```

**Examples:**

```bash
# Interactive reset (with confirmation prompt)
$ clutch emergency-reset --safe-model "llama-7b"
WARNING: This will force-unload all models and restore the cluster
to a known state. This should only be used in emergencies.
Do you want to continue? [y/N]: y
✓ Emergency reset completed
  Primary node: 10.0.0.1
  Safe model loaded: llama-7b

# Non-interactive reset (with --force flag)
$ clutch emergency-reset --safe-model "llama-7b" --force
✓ Emergency reset completed
  Primary node: 10.0.0.1
  Safe model loaded: llama-7b

# Using configuration defaults
$ clutch emergency-reset --force
✓ Emergency reset completed
  Primary node: 10.0.0.1
  Safe model loaded: llama-7b

# With JSON output (for automation)
$ clutch emergency-reset --safe-model "llama-7b" --force --json
{
  "success": true,
  "primary_node": "10.0.0.1",
  "safe_model": "llama-7b",
  "error": null
}
```

**Reset Sequence:**

1. Confirm action (unless `--force` is used)
2. Force-unload any active model (bypasses health checks)
3. Verify primary node is reachable (retries 3 times with exponential backoff)
4. Load the safe model on the primary node

**When to Use Emergency Reset:**

- Cluster is hung and stuck in a `SHIFTING` state
- Model loading failed and left the cluster in a bad state
- You need to restore cluster to minimal functioning state
- Normal upshift/downshift commands are failing

**Exit Codes:**

- `0` — Reset succeeded
- `1` — Reset failed (configuration error or backend error)

---

## Common Workflows

### Agentic Shift Workflow

```bash
#!/bin/bash
# Example: Agent detects complex task and requests upshift

# 1. Check cluster health
if ! clutch check --json | grep -q '"reachable": true'; then
    echo "Cluster unhealthy—skipping upshift"
    exit 1
fi

# 2. Upshift to reasoning model
clutch upshift --model "GPT-OSS-120B" --ram 75000000000

# 3. Run agent with reasoning model
# ... (your agent code here)

# 4. Downshift back to daily driver
clutch downshift --model "Qwen3-Next-80B" --ram 50000000000
```

### Continuous Monitoring

```bash
#!/bin/bash
# Monitor cluster health every 30 seconds

while true; do
    echo "Checking cluster at $(date)"
    clutch check
    sleep 30
done
```

### Automated Recovery

```bash
#!/bin/bash
# If status check fails, attempt recovery

if ! clutch status --json | grep -q '"cluster_health": true'; then
    echo "Cluster unhealthy—attempting emergency reset"
    clutch emergency-reset --force --safe-model "llama-7b"
fi
```

---

## Error Messages and Troubleshooting

| Error Message | Cause | Solution |
| --- | --- | --- |
| `No node IPs configured` | Missing configuration | Create `~/.config/llm-clutch/config.toml` with `node_ips` |
| `Cluster is not healthy` | Nodes unreachable | Run `clutch check` to diagnose; check network/power |
| `Insufficient memory` | Not enough RAM for model | Reduce model size; add more cluster capacity |
| `Failed to unload current model` | Backend error | Use `clutch emergency-reset` to force-unload |
| `Cannot connect to config file` | File permissions | Check `chmod` on `~/.config/llm-clutch/config.toml` |

---

## Configuration File

See [Configuration Guide](config.md) for detailed configuration options and examples.

---

## See Also

- [API Reference](api/clutch.md) — Programmatic usage
- [Configuration Guide](config.md) — Detailed config file documentation
- [Hardware Guide](HARDWARE_GUIDE.md) — Setting up high-speed model transfer infrastructure
