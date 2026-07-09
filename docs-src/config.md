# Configuration Guide

llm-clutch is configured via a TOML file. This guide covers all configuration options, file location, and examples.

## Configuration File Location

By default, llm-clutch looks for the configuration file at:

```
~/.config/llm-clutch/config.toml
```

You can override this by passing `--config` to any CLI command:

```bash
clutch --config /etc/llm-clutch/production.toml status
clutch --config ./dev.toml upshift --model GPT-OSS-120B --ram 75000000000
```

## Creating a Configuration File

1. Create the directory:

```bash
mkdir -p ~/.config/llm-clutch
```

2. Create the configuration file:

```bash
touch ~/.config/llm-clutch/config.toml
```

3. Add your configuration (see sections below)

4. Verify:

```bash
clutch --config ~/.config/llm-clutch/config.toml status
```

## Configuration Options

### Required Settings

#### `node_ips`

List of node IP addresses in your cluster. These are the nodes that llm-clutch will probe for health checks and model management.

**Type:** Array of strings  
**Example:**

```toml
node_ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
```

**Usage:** These IPs should correspond to your Thunderbolt bridge subnet (or your chosen network for model transfer). See [Hardware Guide](HARDWARE_GUIDE.md) for setup details.

#### `exo_api_url`

The base URL for your Exo API endpoint. This is where llm-clutch sends load/unload/status commands.

**Type:** String  
**Example:**

```toml
exo_api_url = "http://10.0.0.1:52415"
```

**Default:** `"http://10.0.0.1:52415"` (if not specified)

**Note:** The default assumes Exo is running on the first node with the standard port 52415.

### Optional Settings

#### `health_check_timeout_seconds`

Timeout in seconds for cluster health checks (TCP socket probes). Lower values are faster but may miss slow nodes.

**Type:** Float  
**Default:** `5`  
**Example:**

```toml
health_check_timeout_seconds = 3  # Quick checks on responsive cluster
health_check_timeout_seconds = 10 # Generous timeout for slow network
```

#### `health_check_port`

TCP port to probe on each node. Should match the port where your LLM runner's API is exposed.

**Type:** Integer  
**Default:** `52415`  
**Example:**

```toml
health_check_port = 52415  # Exo default
health_check_port = 8000   # Custom port
```

#### `safe_model`

Default safe/fallback model to use with `clutch emergency-reset`. If not specified, you must provide `--safe-model` on the command line.

**Type:** String  
**Example:**

```toml
safe_model = "llama-7b"
```

#### `primary_node`

Default primary node IP address for operations like `emergency-reset`. If not specified, defaults to the first node in `node_ips`.

**Type:** String  
**Example:**

```toml
primary_node = "10.0.0.1"
```

## Complete Configuration Example

```toml
# ~/.config/llm-clutch/config.toml

# Required: List of cluster node IPs (on Thunderbolt bridge or model transfer network)
node_ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

# Required: Exo API endpoint
exo_api_url = "http://10.0.0.1:52415"

# Optional: Health check settings
health_check_timeout_seconds = 5
health_check_port = 52415

# Optional: Emergency reset defaults
safe_model = "llama-7b"
primary_node = "10.0.0.1"
```

## Environment Variables

You can override configuration values using environment variables. Environment variables take precedence over the config file.

**Supported Environment Variables:**

| Env Var | Config Key | Type | Example |
| --- | --- | --- | --- |
| `LLM_CLUTCH_NODE_IPS` | `node_ips` | Comma-separated list | `10.0.0.1,10.0.0.2,10.0.0.3` |
| `LLM_CLUTCH_EXO_API_URL` | `exo_api_url` | String | `http://10.0.0.1:52415` |
| `LLM_CLUTCH_HEALTH_CHECK_TIMEOUT` | `health_check_timeout_seconds` | Float | `5` |
| `LLM_CLUTCH_HEALTH_CHECK_PORT` | `health_check_port` | Integer | `52415` |
| `LLM_CLUTCH_SAFE_MODEL` | `safe_model` | String | `llama-7b` |
| `LLM_CLUTCH_PRIMARY_NODE` | `primary_node` | String | `10.0.0.1` |

**Example:**

```bash
# Override via environment variables
export LLM_CLUTCH_NODE_IPS="10.0.0.1,10.0.0.2,10.0.0.3"
export LLM_CLUTCH_EXO_API_URL="http://10.0.0.1:52415"

clutch status
```

**Precedence Order (highest to lowest):**

1. Command-line arguments (e.g., `--node-ips`)
2. Environment variables
3. Configuration file (`~/.config/llm-clutch/config.toml`)
4. Defaults in llm-clutch code

## Production Configuration Examples

### Small Cluster (2-3 Nodes)

```toml
# ~3 nodes, local network, default Exo setup
node_ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
exo_api_url = "http://10.0.0.1:52415"
health_check_timeout_seconds = 5
safe_model = "mistral-7b"
primary_node = "10.0.0.1"
```

### Large Cluster (5+ Nodes)

```toml
# ~5-10 nodes, might be on a separate network
node_ips = [
  "10.0.0.1", "10.0.0.2", "10.0.0.3",
  "10.0.0.4", "10.0.0.5"
]
exo_api_url = "http://10.0.0.1:52415"

# Generous timeout for larger clusters
health_check_timeout_seconds = 10

safe_model = "llama-70b"
primary_node = "10.0.0.1"
```

### High-Latency Network

```toml
# Cluster on a high-latency or congested network
node_ips = ["10.0.0.1", "10.0.0.2"]
exo_api_url = "http://10.0.0.1:52415"

# Longer timeout to accommodate latency
health_check_timeout_seconds = 15

safe_model = "llama-7b"
primary_node = "10.0.0.1"
```

### Docker/Container Deployment

```toml
# Cluster on container network (e.g., Docker Compose)
node_ips = ["exo-node-1", "exo-node-2", "exo-node-3"]  # DNS names work too
exo_api_url = "http://exo-node-1:52415"
health_check_timeout_seconds = 5
safe_model = "llama-7b"
primary_node = "exo-node-1"
```

## Docker and Kubernetes Configuration

### Docker Compose

For Docker Compose, mount the configuration file as a volume:

```yaml
services:
  clutch-client:
    image: python:3.10
    volumes:
      - ~/.config/llm-clutch/config.toml:/root/.config/llm-clutch/config.toml:ro
    entrypoint: |
      bash -c '
        pip install llm-clutch
        clutch status
      '
    networks:
      - cluster-network
```

### Kubernetes

For Kubernetes, create a ConfigMap:

```bash
# Create config file locally
cat > /tmp/config.toml <<EOF
node_ips = ["exo-node-1", "exo-node-2", "exo-node-3"]
exo_api_url = "http://exo-node-1:52415"
EOF

# Create ConfigMap in Kubernetes
kubectl create configmap llm-clutch-config --from-file=/tmp/config.toml
```

Then reference in a Pod:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: clutch-client
spec:
  containers:
  - name: clutch
    image: python:3.10
    volumeMounts:
    - name: config
      mountPath: /root/.config/llm-clutch
  volumes:
  - name: config
    configMap:
      name: llm-clutch-config
      items:
      - key: config.toml
        path: config.toml
```

## Troubleshooting

### "No node IPs configured"

**Problem:** Command fails with "No node IPs configured"

**Solution:**

1. Check config file exists: `cat ~/.config/llm-clutch/config.toml`
2. Verify `node_ips` is set: `grep node_ips ~/.config/llm-clutch/config.toml`
3. If not set, add it: `echo 'node_ips = ["10.0.0.1", "10.0.0.2"]' >> ~/.config/llm-clutch/config.toml`

### Can't Connect to Exo API

**Problem:** Cluster checks fail; can't reach Exo API

**Solution:**

1. Check `exo_api_url` in config matches your Exo deployment:
   ```bash
   clutch --config ~/.config/llm-clutch/config.toml check
   ```

2. Verify Exo is running on the configured node and port:
   ```bash
   curl -s http://10.0.0.1:52415/compute/node/status | jq .
   ```

3. Check firewall/network:
   ```bash
   ping 10.0.0.1
   nc -zv 10.0.0.1 52415
   ```

### Configuration File Not Found

**Problem:** "Cannot load config from `~/.config/llm-clutch/config.toml`"

**Solution:**

1. Create the directory:
   ```bash
   mkdir -p ~/.config/llm-clutch
   ```

2. Create the config file with required settings:
   ```bash
   cat > ~/.config/llm-clutch/config.toml <<EOF
   node_ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
   exo_api_url = "http://10.0.0.1:52415"
   EOF
   ```

### Health Check Timeouts

**Problem:** Health checks fail with "Connection timeout"

**Solution:**

1. Increase `health_check_timeout_seconds` in config:
   ```toml
   health_check_timeout_seconds = 10  # Was 5, now more generous
   ```

2. Check network connectivity:
   ```bash
   ping 10.0.0.1
   ```

3. Verify nodes are responsive:
   ```bash
   curl -s http://10.0.0.1:52415/compute/node/status | jq .
   ```

---

## See Also

- [CLI Reference](cli.md) — Command-line interface
- [Hardware Guide](HARDWARE_GUIDE.md) — Setting up cluster infrastructure
- [API Reference](api/clutch.md) — Programmatic usage
