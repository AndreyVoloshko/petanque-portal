# Testing And Quality Gates Audit

## Summary

Testing is the biggest missing safety net. There is only a placeholder `federation/tests.py` with no test code. No CI configuration exists. No linting or formatting tools are configured.

## Current State

- **Tests:** Zero. Only `from django.test import TestCase` placeholder.
- **CI:** No GitHub Actions, no GitLab CI, no Jenkins config found.
- **Linting:** No ruff, flake8, pylint, or mypy configuration.
- **Formatting:** No black, autopep8, or ruff format configuration.
- **Type checking:** No type annotations, no mypy/pyright.
- **Coverage:** No coverage tool configured.
- **Pre-commit hooks:** None.

## Risks Without Tests

| Scenario | Impact |
|----------|--------|
| Security fix breaks tournament admin flow | Organizers can't manage tournaments |
| Rating logic change introduces off-by-one | All player rankings incorrect |
| Django upgrade breaks template filter | Pages crash in production |
| Dependency update has breaking change | Build works, runtime crashes |
| Refactoring accidentally removes auth check | Security regression |
| Template change breaks HTML structure | Pages render broken for all users |

## What Should Be Tested (Priority Order)

### Layer 1: Smoke Tests (Task 005)

Public pages return HTTP 200:
- Homepage, players, clubs, tournaments, calendar
- API endpoints return valid JSON
- Registration pages render forms
- Admin login page loads
- Error pages work (after fix)

### Layer 2: Security Tests

- Anonymous users cannot POST to tournament mutations
- Authenticated non-admin users cannot modify tournaments
- CSRF protection is active
- Login redirect stays on-domain

### Layer 3: Business Logic Tests (Task 011)

- Rating calculation produces expected outputs for known inputs
- Tournament power calculation works for edge cases
- Player ranking is consistent
- Registration validates correctly

### Layer 4: Integration Tests

- Team registration end-to-end flow
- Tournament processing workflow (power → ratings → close)
- Player rating recalculation with multiple tournaments

## Recommended Tooling

| Tool | Purpose |
|------|---------|
| `pytest` + `pytest-django` | Test runner |
| `factory_boy` | Test data factories |
| `ruff` | Linting + formatting |
| `pip-audit` | Dependency vulnerability scanning |
| `django-pytest-num-queries` | Performance regression tests |
| GitHub Actions | CI pipeline |

## Configuration Needed

```toml
# pyproject.toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "api.settings.test"
python_files = "tests/*.py test_*.py"
addopts = "-v --tb=short"

[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP"]
```

## Quality Baseline Targets

After initial setup (Tasks 005, 011, 015):
- All public pages have smoke tests
- Rating logic has 10+ test cases
- CI runs on every push
- Lint errors are zero
- `pip-audit` has zero critical findings
- Test suite runs in < 60 seconds
