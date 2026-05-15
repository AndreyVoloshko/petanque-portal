# Task 011: Rating Calculation Tests

## Goal

Protect the app's core business value with tests before any refactoring of rating logic.

## Why This Matters

Rating calculation is the most complex and most valuable logic in the codebase. It spans multiple models and methods. Without tests, any change to this logic risks silent regression that corrupts player standings.

## Scope

### Test Infrastructure

- Create fixture factories for: Player, Team, Club, Tournament, TeamTournamentMembership, Season
- Use `pytest` + `pytest-django` with `@pytest.fixture` or `factory_boy`

### Golden-Case Tests

1. **`Tournament.calculate_basic_points(teams_count)`**
   - Input: teams_count=8 → Output: 3 (log2(8))
   - Input: teams_count=16 → Output: 4
   - Input: teams_count=1 → Output: 0

2. **`Tournament.calculate_raw_team_rating_points(basic_points, team_place)`**
   - 1st place gets basic_points
   - 2nd place gets basic_points - 1
   - 3rd-4th place gets calculated recursively
   - Verify the recursive algorithm for places 1-8 with basic_points=3

3. **`TeamTournamentMembership.recalculate_power()`**
   - Team with 2 players: power = sum(player_powers) / 2
   - Team with 3 players: power = sum(player_powers) / 3
   - Empty team: should not crash (guard added in Task 004)

4. **`Tournament.recalculate_power()`**
   - Takes top N teams by power
   - Multiplies by players_in_team_min
   - Verify with known inputs

5. **`Tournament.recalculate_ratings()`**
   - Combines basic_points, raw_team_points, rating_coefficient, tournament_power
   - Verify end-to-end for a small tournament

6. **`Player.recalculate_ratings()`**
   - Takes top N tournaments by points
   - Sums them into current_rating
   - Handles different rating types (standard, b, inclusive)
   - Verify with 2-3 tournaments of known values

### Edge Cases

- Tournament with 1 team
- Player in only 1 tournament
- Player with licence deactivated (should erase ratings)
- Tournament marked as 'away' category (should reject processing)
- Tournament not ready for processing (should reject)

## Acceptance Criteria

- All rating algorithms have at least 2 test cases with known inputs/outputs
- Edge cases don't crash
- Tests document the expected rating behavior (serve as specification)
- Tests pass before service extraction (Task 014)
- Test run < 10 seconds

## Complexity

L

## Risk

High — understanding the recursive rating algorithm correctly is critical. Wrong test expectations could validate wrong behavior.

## Big Win

High — enables safe refactoring of the most valuable business logic.
