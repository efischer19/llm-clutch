# Hardware Guide: Fast Model Transfer Architecture

## Overview

**llm-clutch is designed to work with any cluster topology**, but for optimal performance—loading massive models (75GB+) in under 60 seconds—we recommend a dedicated high-speed network for model transfers.

This guide explains the principles of fast model loading and provides a concrete setup example using a Thunderbolt-over-NFS architecture on Apple Silicon Macs. If you're using different hardware, the underlying concepts remain the same: **dedicate a fast, isolated network for model weights and use read-optimized file sharing**.

### Why Fast Model Transfer Matters

With standard 1 Gigabit Ethernet:
- Loading a 75GB model takes **10-15 minutes** 🐢
- Your agent workflow is stalled during the entire transfer
- GPU/NPU clusters sit idle waiting for weights

With Thunderbolt + NFS:
- Loading a 75GB model takes **under 60 seconds** 🚀
- Agent workflows resume almost immediately
- Cluster efficiency dramatically improves

## Principles: Building a Fast Model Transfer System

Regardless of your hardware, a good model transfer setup needs:

1. **Dedicated High-Speed Network** — Don't share this with regular traffic
   - Isolated from your regular cluster networking (different subnet, separate hardware if possible)
   - Low-latency, high-bandwidth connection (>500 Mbps, ideally >1 Gbps)

2. **Centralized Storage** — One machine holds the model weights
   - Fast internal storage (NVMe SSD, not HDD)
   - Enough capacity for all your models
   - Can be the same as a compute node, but shouldn't be overloaded

3. **Read-Optimized File Sharing** — Use lightweight protocols
   - NFS is excellent for read-only model access (avoids SMB overhead)
   - Lower latency than SMB/CIFS
   - Better saturation of network bandwidth

4. **Consistent Addressing** — Predictable node IPs
   - Static IP addresses on the isolated network
   - DNS resolution (optional, but helpful for config management)

## Concrete Example: Apple Silicon Mac Cluster

This section walks through setting up llm-clutch with Thunderbolt bridging on a cluster of Macs.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Node 1: Mac Studio (Primary)          │
│  - M1 Max (40 cores, 64GB unified memory)                   │
│  - Internal NVMe SSD (4TB) holds model weights              │
│  - Exo backend runs here (or runs on workers)              │
│  - Shares /Users/Shared/exo_models over NFS               │
└──────────────────┬──────────────────┬──────────────────────┘
                   │                  │
              Thunderbolt 4       Thunderbolt 4
              Bridge Cable         Bridge Cable
             (10-20 Gbps)         (10-20 Gbps)
                   │                  │
        ┌──────────┴─────────┬────────┴──────────┐
        │                    │                   │
        ▼                    ▼                   ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Node 2: MacBook │  │  Node 3: Mac Mini│  │  (Optional) Node 4
│  M2 Pro          │  │  M4 Pro          │  │  ...
│  16GB RAM        │  │  16GB RAM        │  │
│  Mounts NFS at:  │  │  Mounts NFS at:  │  │
│  /mnt/models     │  │  /mnt/models     │  │
└──────────────────┘  └──────────────────┘  └──────────────────┘

                    10.0.0.0/24 Subnet
                    (Thunderbolt Bridge)
```

### Step 1: Physical Setup

Connect all your Mac nodes using **Thunderbolt 4 cables**:

- **Option A (Daisy-chain):** If your Macs support daisy-chaining, connect them sequentially
  - Node 1 → Node 2 → Node 3 → (Optional) Node 4
  - Limits: Check your Mac model's daisy-chain capability (newer M-series Macs support this)

- **Option B (Star topology):** Use a Thunderbolt dock or hub on the primary node
  - Node 1 (with dock/hub) ← Node 2
  - Node 1 (with dock/hub) ← Node 3
  - Node 1 (with dock/hub) ← Node 4
  - More reliable, minimal latency, allows dynamic node addition

### Step 2: Configure Thunderbolt Bridge Network

Create an isolated IP subnet over the Thunderbolt bridge for fast, direct model access.

**On all Macs (Nodes 1, 2, 3, ...):**

1. Open **System Preferences → Network**
2. Locate **Thunderbolt Bridge** (a new interface, separate from WiFi/Ethernet)
3. Click **Advanced...** (or **Details...**) then select the **TCP/IP** tab
4. Change "Configure IPv4" from **DHCP** to **Manually**
5. Assign static IP addresses:
   - **Node 1 (Primary):** 10.0.0.1 / Subnet Mask 255.255.255.0
   - **Node 2 (Worker 1):** 10.0.0.2 / Subnet Mask 255.255.255.0
   - **Node 3 (Worker 2):** 10.0.0.3 / Subnet Mask 255.255.255.0
   - *Continue incrementing for additional nodes*

6. Click **OK** and apply the network configuration

**Verify connectivity:**

From Node 2 or Node 3, open Terminal and test:

```bash
ping -c 4 10.0.0.1
```

Expected output:
```
PING 10.0.0.1 (10.0.0.1): 56 data bytes
64 bytes from 10.0.0.1: icmp_seq=0 ttl=64 time=0.5 ms
64 bytes from 10.0.0.1: icmp_seq=1 ttl=64 time=0.4 ms
64 bytes from 10.0.0.1: icmp_seq=2 ttl=64 time=0.6 ms
```

If you see response times **< 1 ms**, the bridge is working correctly.

### Step 3: Set Up NFS for Model Storage

NFS (Network File System) is ideal for model distribution because it has **very low overhead** compared to SMB/CIFS, allowing you to saturate the Thunderbolt bandwidth.

#### On Node 1 (Primary/Storage Node):

**A. Download your models:**

```bash
# Create a dedicated directory for models
mkdir -p /Users/Shared/exo_models

# Download models using Exo or huggingface-cli
# (This step is model-specific; adjust as needed)
cd /Users/Shared/exo_models

# Example: using huggingface-cli (if installed)
huggingface-cli download --cache-dir . gpt-oss-120b

# Or download via Exo's model management (depends on your Exo setup)
```

**B. Export the directory via NFS:**

```bash
# Edit the NFS exports file
sudo nano /etc/exports
```

Add this line (all on one line):

```
/Users/Shared/exo_models -network 10.0.0.0 -mask 255.255.255.0 -ro -mapall=nobody
```

**Explanation:**
- `-network 10.0.0.0 -mask 255.255.255.0` — Only allow access from the Thunderbolt subnet
- `-ro` — Read-only (prevents accidental writes, keeps models safe)
- `-mapall=nobody` — Map all requests to the `nobody` user (no special permissions needed)

**C. Enable and start NFS:**

```bash
# Enable NFS daemon
sudo nfsd enable

# Restart NFS to apply changes
sudo nfsd update

# Verify NFS is running
sudo nfsd status
```

#### On Nodes 2, 3, ... (Worker Nodes):

**A. Create a mount point:**

```bash
# Create an empty directory to attach the NFS share
sudo mkdir -p /mnt/models
```

**B. Mount the NFS share:**

```bash
# Mount read-only from the primary node
sudo mount -t nfs -o ro 10.0.0.1:/Users/Shared/exo_models /mnt/models
```

**Verify the mount:**

```bash
ls -la /mnt/models
```

You should see your model directories listed.

**C. (Optional) Persist across reboots:**

To automatically mount on boot, add this line to `/etc/fstab`:

```bash
# Edit fstab
sudo nano /etc/fstab

# Add this line:
10.0.0.1:/Users/Shared/exo_models /mnt/models nfs ro,auto 0 0

# Save and exit (Ctrl+X, then Y, then Enter)

# Test that it works on next mount attempt
sudo mount -a
```

### Step 4: Configure Exo to Use the NFS Mount

When Exo starts on your worker nodes, tell it to load models from the NFS mount instead of downloading them.

**On Nodes 2, 3, ... (Worker Nodes):**

Set an environment variable before starting Exo:

```bash
# Add to ~/.bashrc or ~/.zshrc (for persistence)
export EXO_MODELS_READ_ONLY_DIRS="/mnt/models"

# Or set it inline when starting Exo
EXO_MODELS_READ_ONLY_DIRS="/mnt/models" uv run exo
```

**On Node 1 (Primary):**

If Exo runs on the primary node, it can use local models directly:

```bash
export EXO_MODELS_DIR="/Users/Shared/exo_models"
uv run exo
```

### Step 5: Configure llm-clutch

Create a configuration file at `~/.config/llm-clutch/config.toml`:

```toml
[llm_clutch]
# Point to the Exo API (could be Node 1 or another node)
exo_api_url = "http://10.0.0.1:52415"

# List all worker nodes in the cluster
node_ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

# (Optional) Timeout for node health checks
health_check_timeout_seconds = 5

# (Optional) Port for node health checks (should match Exo's API port)
health_check_port = 52415
```

## Performance Tips

### Measuring Transfer Speed

Once your NFS mount is active, measure the actual transfer speed:

```bash
# On a worker node, copy a large file from the NFS mount
# (Use a model file or create a test file)
dd if=/mnt/models/large_model_file of=/dev/null bs=1M

# You should see throughput of 1,500+ MB/s on Thunderbolt 4
# Standard Gigabit Ethernet: ~100-125 MB/s
# WiFi: 50-150 MB/s
```

### Network Optimization (Mac-specific)

If you're seeing lower-than-expected speeds:

1. **Check network MTU:**
   ```bash
   # Should show 1500 for Thunderbolt Bridge
   networksetup -getMTU Thunderbolt\ Bridge
   ```

2. **Reduce NFS mounting overhead:**
   ```bash
   # Remount with optimized options
   sudo mount -t nfs -o ro,bg,hard,intr,tcp,nfsvers=3 10.0.0.1:/Users/Shared/exo_models /mnt/models
   ```

3. **Monitor NFS performance:**
   ```bash
   # On macOS with nfs3stat (if available)
   nfsstat -c
   ```

## Alternatives: Non-Mac Clusters

If you're using Linux or other hardware, the same principles apply—adapt to your infrastructure:

| Component | Mac Example | Linux Alternative |
| --- | --- | --- |
| **Fast Network** | Thunderbolt 4 Bridge (10-20 Gbps) | 10 GbE, InfiniBand, or Direct Attach |
| **Storage Node** | Mac Studio (internal NVMe) | Dedicated Linux server with fast SSD |
| **File Sharing** | NFS (read-only) | NFS or distributed storage (GlusterFS, Ceph) |
| **Subnet Configuration** | macOS Network Settings | Linux `netplan`, `nmcli`, or equivalent |

The **logical architecture** remains the same: isolated high-speed network → centralized fast storage → read-optimized sharing → local cluster nodes.

## Troubleshooting

| Problem | Diagnosis | Solution |
| --- | --- | --- |
| **Nodes can't ping** | Run `ping 10.0.0.1` on a worker | Check Thunderbolt connection; verify static IPs are configured |
| **NFS mount fails** | `sudo mount ...` returns "Permission denied" | Verify `/etc/exports` on primary; ensure IP is in allowed subnet |
| **Slow transfers** | `dd` shows <500 MB/s | Check NFS mount options; verify Thunderbolt connection quality |
| **Models not found** | Exo can't locate models | Verify `/mnt/models` mount point; check `EXO_MODELS_READ_ONLY_DIRS` environment variable |

## Next Steps

Once your hardware is set up:

1. **Test with llm-clutch:** Follow the [Quick Start](index.md) guide
2. **Monitor cluster health:** Use `clutch status` and `clutch check` commands
3. **Measure performance:** Track upshift/downshift times to ensure sub-minute model loads
4. **Iterate:** Adjust NFS mount options, network settings, or hardware as needed

For more details on llm-clutch configuration and usage, see the [Configuration Guide](config.md) and [CLI Reference](cli.md).
