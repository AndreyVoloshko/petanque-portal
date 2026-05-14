# Data Model And Domain Logic Audit

## Summary

The domain model is understandable: players, clubs, teams, tournaments, seasons, records, documents, national teams, and departments. The risk is that important business rules are distributed across models, admin actions, views, and template filters.

## Core Domain Areas

- Player profile, license state, ratings, coach/arbiter/sport-title data.
- Team composition and captain membership.
- Tournament registration, teams, arbiters, processing state, power, and rating points.
- Seasons and historical ratings.
- Clubs/cities.
- Documents and document categories.
- National team memberships.
- Department memberships.

## Domain Logic Hotspots

### Rating Calculation

Rating logic is spread across:

- `Player.recalculate_ratings()`
- `Tournament.recalculate_ratings()`
- `Tournament.calculate_basic_points()`
- `Tournament.calculate_raw_team_rating_points()`
- `TeamTournamentMembership.recalculate_power()`
- admin actions
- scheduled command

This is core business value and should be covered by tests before any refactor.

### Tournament Registration

Registration involves:

- dynamic form fields
- player lookup
- duplicate participant check
- team creation/reuse
- tournament membership creation
- power recalculation

This should be moved behind a service with tests.

### Permission Rules

Permission rules are embedded in:

- `Tournament.is_user_has_admin_access_to_tournament()`
- `TeamTournamentMembership.is_user_has_admin_access_to_team()`
- view-level checks
- template filters

This should be centralized enough that all mutation views use the same checks.

## Recommended Domain Refactor

Create service modules after smoke tests are in place:

```text
federation/services/rating_calculation.py
federation/services/tournament_registration.py
federation/services/tournament_processing.py
federation/permissions.py
```

Start by moving code without changing behavior, then add tests around extracted functions.

