# Task 014: Rating And Tournament Service Extraction

## Goal

Move tournament processing and rating workflows out of fat models into testable service modules.

## Prerequisites

- Task 011 (Rating Calculation Tests) must be complete — tests protect against behavioral regressions.
- Task 010 (Tournament Registration Service) demonstrates the pattern.

## Scope

### Create Service Modules

```
federation/services/
├── __init__.py
├── rating_calculation.py      ← Player.recalculate_ratings() logic
├── tournament_processing.py   ← Tournament.recalculate_power(), close_for_processing()
└── tournament_registration.py ← Already created in Task 010
```

### Move Logic Incrementally

**Step 1:** Extract pure calculation functions (no DB, easy to test):
- `calculate_basic_points(teams_count)` → pure math
- `calculate_raw_team_rating_points(basic_points, team_place)` → recursive pure math

**Step 2:** Extract coordination functions:
- `recalculate_tournament_power(tournament)` → orchestrates team power recalc
- `recalculate_tournament_ratings(tournament)` → orchestrates rating point assignment
- `close_tournament_for_processing(tournament)` → validates + triggers player recalc

**Step 3:** Extract player rating:
- `recalculate_player_ratings(player)` → fetches tournaments, computes ratings

### Keep Model Wrappers

Existing code calls `tournament.recalculate_power()` from admin actions. Keep thin wrappers:
```python
class Tournament(models.Model):
    def recalculate_power(self):
        from federation.services.tournament_processing import recalculate_tournament_power
        recalculate_tournament_power(self)
```

This maintains backward compatibility while making the logic testable in isolation.

### Update Admin Actions

Admin actions in `admin_actions/tournament.py` should call service functions directly after extraction:
```python
def recalculate_power(modeladmin, request, queryset):
    for tournament in queryset:
        try:
            recalculate_tournament_power(tournament)
        except Exception as e:
            messages.error(request, str(e))
```

## Acceptance Criteria

- All rating tests from Task 011 still pass
- Admin actions still work
- Model methods become thin wrappers calling services
- Services are independently testable (can be tested with minimal DB setup)
- Behavior is unchanged — same inputs produce same outputs
- Weekly cron job still works

## Complexity

XL

## Risk

High — this touches the most critical business logic. Must be done incrementally with tests verifying each step.

## Big Win

High — enables confident changes to rating logic, easier debugging, and potential future optimizations.
