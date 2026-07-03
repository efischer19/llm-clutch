# Ticket 11: CI/CD & PyPI Publishing

**Title:** `feat: [configure CI/CD pipelines and PyPI publishing for llm-clutch]`

**Labels:** `enhancement`

## What do you want to build?

Update the GitHub Actions CI/CD workflows (per ADR-014) to support
llm-clutch with uv-based dependency management, and configure the PyPI
publishing pipeline so the package can be released with version tags.

## Acceptance Criteria

- [ ] The CI composite action is updated (or a new one created) to support uv instead of Poetry: installs uv, creates `.venv`, caches dependencies
- [ ] `ci.yml` workflow runs for `libs/llm-clutch/`: `uv run ruff format --check .`, `uv run ruff check .`, `uv run pytest`
- [ ] `publish.yml` workflow is updated to use `uv build` and `uv publish` for PyPI releases
- [ ] The publish workflow triggers on version tags (e.g., `v0.1.0`) and manual dispatch
- [ ] PyPI publishing requires the `PYPI_TOKEN` secret (documented but not committed)
- [ ] Docker workflow is updated if llm-clutch includes a Dockerfile (optional for a library)
- [ ] Documentation workflow (`documentation.yml`) builds and deploys updated docs on push to `main`
- [ ] Dependabot configuration is updated to monitor `libs/llm-clutch/` dependencies
- [ ] All workflows pass on a test PR
- [ ] `README.md` includes CI status badges

## Implementation Notes

- The existing `setup-python-poetry` composite action needs to be
  replaced or supplemented with a `setup-python-uv` action. Since this
  is a project-wide change (affects all apps/libs), consider making the
  uv action the new default and updating the example-app/example-lib
  as well, or keeping both actions during a transition period.
- For uv in CI, the recommended approach is:

  ```yaml
  - uses: astral-sh/setup-uv@v5
  - run: uv sync
  - run: uv run pytest
  ```

- The publish step should use `uv build` to create sdist and wheel, then
  `uv publish` (or `twine upload`) to push to PyPI.
- Consider adding a `test-publish` job that publishes to TestPyPI on PRs
  to validate the packaging before real releases.
- Update `.github/dependabot.yml` to add a `pip` entry for
  `libs/llm-clutch/`.
- ADR-014 references Poetry throughout — once ADR-015 is accepted, the
  CI/CD strategy ADR may also need updating to reflect uv. This can be
  a follow-up or handled in this ticket.
