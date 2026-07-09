# llm-clutch

A hardware-aware, local LLM orchestration package that safely hot-swaps massive neural networks in memory across a local cluster.

## Why llm-clutch?

Running a local multi-node AI cluster (e.g., using [Exo](https://github.com/exo-explore/exo)) presents a fundamental tradeoff:

- **A fast, efficient model** (like Qwen3-Next-80B) is great for everyday tasks
- **A heavyweight reasoning model** (like GPT-OSS-120B) is needed for complex agentic workflows

The problem: Copying 75GB+ model weights across your network or reading them from a slow NAS takes 10-15 minutes, stalling your agent.

**llm-clutch solves this** by managing high-speed hot-swaps using a Thunderbolt-bridged NFS architecture. More importantly, it acts as a traffic cop (a "synchromesh") that verifies cluster topology and available unified memory *before* dropping the current model and loading the new one, preventing cluster crashes.

The package uses a **manual transmission metaphor** to make model state management intuitive:
- **rev_match()** — Pre-flight safety check that the cluster is online and has enough memory
- **disengage()** — Unload the current model
- **engage()** — Load a new model
- **upshift()** — Move from daily-driver to heavy-reasoning model
- **downshift()** — Return to the fast daily driver

## Quick Start

### Installation

```bash
pip install llm-clutch
```

### Basic Usage

**Python API:**
```python
import asyncio
from llm_clutch import LLMClutch
from llm_clutch.backend.exo import ExoBackend
from llm_clutch.core.infra import InfraManager

async def main():
    # Configure your cluster
    backend = ExoBackend(base_url="http://10.0.0.1:52415")
    infra = InfraManager(node_ips=["10.0.0.1", "10.0.0.2", "10.0.0.3"])
    
    # Create the clutch engine
    clutch = LLMClutch(backend=backend, infra_manager=infra)
    
    # Upshift to the reasoning model
    result = await clutch.upshift(
        heavy_model="GPT-OSS-120B",
        required_ram=75_000_000_000  # 75GB
    )
    
    if result.success:
        print(f"Successfully loaded {result.new_model}")
    else:
        print(f"Upshift failed: {result.error}")
    
    # Downshift back to the daily driver
    result = await clutch.downshift(
        light_model="Qwen3-Next-80B",
        required_ram=50_000_000_000
    )

asyncio.run(main())
```

**CLI Usage:**
```bash
# Check cluster status
clutch status

# Upshift to reasoning model
clutch upshift "GPT-OSS-120B" --ram 75000000000

# Downshift back to daily driver
clutch downshift "Qwen3-Next-80B" --ram 50000000000

# Emergency reset
clutch emergency-reset
```

## Supported Backends

### Exo (v1.0)
The primary backend for llm-clutch v1.0. [Exo](https://github.com/exo-explore/exo) is a distributed inference framework that splits large language models across multiple nodes.

**Configuration:**
```toml
[llm_clutch]
exo_api_url = "http://10.0.0.1:52415"
node_ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
```

### Implementing a Custom Backend
To add support for a different LLM runner, implement the `ModelBackend` abstract class:

```python
from llm_clutch.backend.base import ModelBackend

class MyBackend(ModelBackend):
    async def load_model(self, model_name: str) -> None:
        """Load model into cluster memory."""
        pass
    
    async def unload_model(self) -> None:
        """Unload currently active model."""
        pass
    
    async def get_available_memory(self) -> int:
        """Return available unified memory in bytes."""
        pass
    
    async def get_active_model(self) -> str | None:
        """Return the name of the currently loaded model."""
        pass
```

See the [API Reference](https://efischer19.github.io/llm-clutch/api/backend/) for details.

## Hardware Setup (Optional but Recommended)

For optimal performance, llm-clutch can leverage a high-speed **Thunderbolt-over-NFS architecture** to load models in under 60 seconds. This setup is **optional** — llm-clutch works with any cluster topology, but performance will depend on your network.

See the [Hardware Guide](https://efischer19.github.io/llm-clutch/hardware-guide/) for setup instructions tailored to your infrastructure.

## Documentation

- **[Full Documentation](https://efischer19.github.io/llm-clutch/)** — Complete guides, API reference, and configuration
- **[Hardware Guide](https://efischer19.github.io/llm-clutch/hardware-guide/)** — Setting up fast model transfer infrastructure
- **[CLI Reference](https://efischer19.github.io/llm-clutch/cli/)** — All CLI commands with examples
- **[API Reference](https://efischer19.github.io/llm-clutch/api/)** — Detailed class and method documentation
- **[Configuration Guide](https://efischer19.github.io/llm-clutch/config/)** — TOML format and environment variables

## Contributing

We welcome contributions! To set up a development environment:

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (replaces pip, venv, and pyproject.toml parsers)

### Setup

```bash
# Clone the repository
git clone https://github.com/efischer19/llm-clutch.git
cd llm-clutch/libs/llm-clutch

# Install dependencies with uv
uv sync

# Run tests
uv run pytest

# Run linting
uv run ruff check .
uv run ruff format --check .

# Build docs locally (from repository root)
cd ../..
uv run -d docs-requirements.txt mkdocs serve
```

### Code Style
- Use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting (automatic on commit via pre-commit hooks)
- Write comprehensive docstrings following [PEP 257](https://peps.python.org/pep-0257/)
- Include type hints for all function arguments and return values
- Add tests for all new functionality

See the repository's [Development Philosophy](https://github.com/efischer19/llm-clutch/blob/main/meta/DEVELOPMENT_PHILOSOPHY.md) and [Contributing Guide](https://efischer19.github.io/llm-clutch/contributing/) for more details.

## License

Licensed under the MIT License. See [LICENSE](../../LICENSE.md) for details.
