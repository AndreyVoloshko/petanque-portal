# Task 010: Tournament Registration Service

## Goal

Extract team registration workflow from forms/views/models into a tested service.

## Scope

- Create `federation/services/tournament_registration.py`.
- Move duplicate player validation, team lookup/creation, tournament membership creation, and power recalculation coordination into service functions.
- Refactor `RegistrationTeamForm` to use idiomatic `clean()` and `clean_<field>()`.
- Keep templates unchanged where possible.

## Key Behaviors To Preserve

- Player cannot register twice for same tournament
- Invalid player IDs return validation errors, not 500s
- Team is created or reused based on player composition
- Power is recalculated after registration
- Captain is the first player in the reversed list
- Reserve players (beyond `number_of_players_in_team_min`) are optional

## Acceptance Criteria

- Player cannot register twice for same tournament
- Invalid player IDs return validation errors, not 500s
- Existing registration page still works
- Service has tests covering:
  - Successful registration
  - Duplicate player detection
  - Invalid player ID handling
  - Team reuse logic
  - Registration with reserve players

## Complexity

L

## Risk

Medium

## Big Win

High
