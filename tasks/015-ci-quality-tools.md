# Task 015: CI And Quality Tools

## Goal

Automate basic quality gates so regressions are caught before deployment.

## Scope

### Linting and Formatting

1. Add `ruff` for linting and formatting:
   ```toml
   # pyproject.toml
   [tool.ruff]
   target-version = "py311"
   line-length = 120

   [tool.ruff.lint]
   select = ["E", "F", "W", "I", "B", "UP"]
   ```

2. Run initial format pass (separate commit).

### CI Pipeline

3. Add GitHub Actions workflow (`.github/workflows/ci.yml`):
   ```yaml
   - Run linter (ruff check)
   - Run formatter check (ruff format --check)
   - Run tests (pytest)
   - Run pip-audit for vulnerabilities
   - Run Django system checks (manage.py check)
   ```

### Pre-commit (Optional)

4. Consider `.pre-commit-config.yaml` with ruff hooks for local development.

### Dependency Audit

5. Add `pip-audit` to CI to catch known vulnerabilities.

## Acceptance Criteria

- CI runs tests on every push/PR
- CI fails on test failures or syntax errors
- CI fails on critical vulnerability in dependencies
- Formatting/linting process is documented
- Developers can run same checks locally with one command

## Complexity

M

## Risk

Low

## Big Win

Medium — prevents regressions from reaching production.
