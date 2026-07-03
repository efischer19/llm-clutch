# python-project-blueprint

> A template for Python monorepo projects targeting Python 3.12+ with Poetry
> dependency management.

## What Is This?

This is a **GitHub template repository** for bootstrapping Python monorepo
projects. It provides the directory structure, tooling decisions, and
configuration needed for a well-organized Python project using modern tools
and best practices.

Built on the [blueprint-repo-blueprints](https://github.com/efischer19/blueprint-repo-blueprints)
foundation, this template adds Python-specific structure, tooling ADRs, and
development conventions.

## How to Use This Template

1. Click the **"Use this template"** button at the top of the repository
   page on GitHub.
2. Choose a name for your new repository.
3. Clone your new repository and begin adding your applications and
   libraries.

For more details on GitHub template repositories, see the
[official documentation](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository).

## What's Included

| Path | Purpose |
| :--- | :--- |
| `apps/` | Standalone Python applications, each with its own `pyproject.toml` |
| `libs/` | Shared Python libraries used across applications |
| `testing/` | Shared test utilities, fixtures, and helpers |
| `scripts/` | Utility and automation scripts |
| `templates/` | Template files for scaffolding new apps and libs |
| `meta/adr/` | Architecture Decision Records — the logbook of *why* decisions were made |
| `meta/plans/` | Project plans and roadmaps |
| `docs-src/` | Source files for generated documentation (MkDocs) |
| `.github/` | GitHub-specific configuration (issue templates, PR templates, CI workflows) |

### Key Tooling Decisions (ADRs)

| ADR | Decision |
| :--- | :--- |
| [ADR-002](meta/adr/ADR-002-use_python312.md) | Python 3.12+ as minimum version |
| [ADR-003](meta/adr/ADR-003-use_poetry.md) | Poetry for dependency management |
| [ADR-004](meta/adr/ADR-004-use_pytest.md) | pytest for testing |
| [ADR-005](meta/adr/ADR-005-use_ruff.md) | Ruff for linting and formatting |
| [ADR-006](meta/adr/ADR-006-use_docker.md) | Docker for containerization |
| [ADR-007](meta/adr/ADR-007-monorepo_apps_structure.md) | Monorepo /apps structure |

See `meta/adr/` for the full list of Architecture Decision Records.

### Key Files

* **`LICENSE.md`** — MIT License
* **`CODE_OF_CONDUCT.md`** — Contributor Covenant Code of Conduct
* **`SECURITY.md`** — Security policy and vulnerability reporting
* **`CONTRIBUTING.md`** — Guidelines for contributing to the project
* **`.python-version`** — Python version specification (3.12)

## Getting Started

After creating a new repository from this template:

### 1. Replace Template Placeholders

Search the repository for the following placeholders and replace them with
values appropriate for your project:

| Placeholder | Description | Example |
| :--- | :--- | :--- |
| `{{PROJECT_NAME}}` | Your repository / project name | `my-python-project` |
| `{{GITHUB_OWNER}}` | GitHub username or organization | `my-org` |
| `{{APP_NAME}}` | Application directory name (in `apps/`) | `api-service` |
| `{{LIB_NAME}}` | Library directory name (in `libs/`) | `core-utils` |

### 2. Set Up Local Development

```bash
# Install Python 3.12+ (use pyenv or your preferred method)
pyenv install 3.12
pyenv local 3.12

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run local quality checks
./scripts/local-ci-check.sh

# Build documentation (optional)
pip install -r docs-requirements.txt
./scripts/build-docs.sh
```

### 3. Create Your First Application

```bash
mkdir -p apps/my-app
cd apps/my-app
poetry init
mkdir -p src/my_app tests
```

### 4. Verify CI

Push a change or open a pull request to confirm the CI workflow runs and
passes in your new repository.

## Design Principles

* **Python 3.12+ only.** Take advantage of modern Python features and
  performance improvements.
* **Poetry everywhere.** Consistent dependency management across all apps
  and libraries.
* **Ruff for speed.** Fast linting and formatting that replaces multiple
  tools.
* **Documentation-first.** Every significant decision is captured in an ADR.
* **AI-friendly.** The structure and conventions are designed to work well
  with AI-assisted development workflows.

## License

This project is licensed under the [MIT License](./LICENSE.md).
