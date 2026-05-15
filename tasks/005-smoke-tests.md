# Task 005: Smoke Test Suite

## Goal

Add a first layer of automated tests that catches obvious page breakage, so future changes can be verified quickly.

## Why This Matters

Every future task depends on knowing whether the app still works after changes. Without tests, the only verification is manual browser testing, which is slow and incomplete.

## Scope

### Test Infrastructure Setup

1. Add `pytest`, `pytest-django` to requirements.
2. Create `pytest.ini` or `pyproject.toml` configuration.
3. Create test database settings (use SQLite or a test PostgreSQL).
4. Add a `conftest.py` with basic fixtures (anonymous client, authenticated user, sample data).

### Smoke Tests (HTTP 200 checks)

Test that public pages return 200:
- `/` (main page)
- `/players/`
- `/players/licence/`
- `/clubs/`
- `/tournaments/`
- `/tournaments/past/`
- `/calendar/`
- `/arbiters/`
- `/coaches/`
- `/records/`
- `/documents/`
- `/departments/`
- `/national_teams/`
- `/statistics/`
- `/login/`

### API Endpoint Tests

- `/api/tournaments/list/?start=...&end=...` returns valid JSON array
- `/api/players_clubs_and_tournaments/list/?typedText=test` returns JSON array
- `/api/players_list/list/?q=test` returns JSON with `results` key

### Form Tests

- GET `/register/player/` returns 200 with form
- GET `/register/team/<id>` returns 200 with form (requires tournament fixture)
- POST to registration with invalid data returns form errors, not 500

### Auth Tests

- Unauthenticated access to `/profile/` redirects to login
- POST to tournament without auth returns 403 (after Task 002 fix)
- Login with valid credentials redirects to profile

### Edge Cases

- Statistics page with no tournaments doesn't crash
- Player detail page with no tournaments shows empty state
- Tournament detail page with no teams renders correctly

## Acceptance Criteria

- Tests run with one command: `pytest` or `make test`
- Tests do not require production credentials or S3 access
- Tests pass in local Docker environment and in CI
- All smoke tests pass on current codebase (or document known failures)
- Test run takes < 30 seconds

## Technical Notes

- Use Django test client (no browser needed for smoke tests)
- Create minimal fixtures: 1 player, 1 club, 1 tournament, 1 team
- For S3-dependent code, either mock storage or use `FileSystemStorage` in test settings
- Consider using `factory_boy` for fixtures if data setup is complex

## Complexity

M

## Risk

Low — tests don't change production code.

## Big Win

High — enables safe changes for all subsequent tasks.
