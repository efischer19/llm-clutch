# Local Development Dependencies

> Tools required for local development.

## Required Tools

| Tool | Version | Purpose | Install |
| :--- | :--- | :--- | :--- |
| **Python** | 3.12+ | Runtime | [python.org](https://www.python.org/) or `pyenv install 3.12` |
| **uv** | 0.1.x+ | Dependency management | [astral.sh/uv](https://docs.astral.sh/uv/) |
| **Git** | 2.x | Version control | [git-scm.com](https://git-scm.com/) |

## Recommended Tools

| Tool | Purpose | Install |
| :--- | :--- | :--- |
| **pyenv** | Python version management | [github.com/pyenv/pyenv](https://github.com/pyenv/pyenv) |
| **pre-commit** | Git hook management | `pip install pre-commit` |
| **Docker** | Containerization | [docker.com](https://www.docker.com/) |
| **markdownlint-cli2** | Markdown linting | `npm install -g markdownlint-cli2` |

## Quick Setup

```bash
# 1. Install Python 3.12+ (using pyenv)
pyenv install 3.12
pyenv local 3.12

# 2. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 4. Install all project dependencies
uv sync

# 5. Verify everything works
./scripts/local-ci-check.sh
```

## Python Version

The minimum Python version for this project is **3.12**, as specified in
`.python-version` and documented in
[ADR-002](meta/adr/ADR-002-use_python312.md).

Use `pyenv` to manage Python versions:

```bash
pyenv install 3.12
pyenv local 3.12
python --version  # Should output Python 3.12.x
```

## uv

uv is a fast Python package manager. See
[ADR-015](meta/adr/ADR-015-use_uv.md).

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync

# Run a command in the project's virtual environment
uv run pytest

# Run formatting
uv run ruff format .

# Run linting
uv run ruff check .
```

## Ruff

Ruff handles both linting and formatting for Python code. See
[ADR-005](meta/adr/ADR-005-use_ruff.md).

```bash
# Check formatting
uv run ruff format --check .

# Auto-format
uv run ruff format .

# Lint
uv run ruff check .

# Lint with auto-fix
uv run ruff check --fix .
```

## Pre-commit

Pre-commit runs quality checks automatically before each commit:

```bash
pip install pre-commit
pre-commit install

# Run all hooks manually
pre-commit run --all-files
```
