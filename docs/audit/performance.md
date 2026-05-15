# Performance Audit

## Summary

The primary performance bottleneck is database query volume caused by template filters that execute queries per rendered row, combined with zero use of `select_related()`/`prefetch_related()` anywhere in the codebase. The statistics page additionally performs O(n*m) Python computation.

## Critical Performance Issues

### 1. Template Filters Execute N+1 Database Queries

**File:** `federation/templatetags/app_filters.py`

These filters are called once per row in list templates:

| Filter | Line | Queries Per Call | Used On |
|--------|------|-----------------|---------|
| `get_number_of_players()` | 120 | 1 COUNT | clubs list |
| `get_club_rating_points()` | 125 | 1 query + N player reads | clubs list |
| `get_club_avg_rating_points()` | 136 | 1 query + N player reads | clubs list |
| `team_short_name_in_tournament()` | 388 | 2 queries | player tournaments |
| `team_rating_points_in_tournament()` | 394 | 2 queries | player tournaments |
| `team_power_in_tournament()` | 401 | 2 queries | player tournaments |
| `team_min_place_in_tournament()` | 408 | 2 queries | player tournaments |
| `team_place_in_tournament()` | 420 | 2 queries | player/tournament pages |
| `team_place_in_tournament_for_admin()` | 443 | 2 queries | tournament admin |
| `player_national_teams()` | 295 | 1 query | player detail |
| `player_records()` | 320 | 1 query | player detail |
| `rating_position()` | 516 | 1 COUNT query | player list/cards |
| `players_in_seasons()` | 552 | 1 COUNT query | player seasons |

**Example impact:** The `/clubs/` page with 20 clubs calls `get_number_of_players()`, `get_club_rating_points()`, and `get_club_avg_rating_points()` per club. That's 20 * 3 = 60 additional queries minimum, with `get_club_rating_points` iterating all players per club.

### 2. `rating_position()` Is O(n) Per Player

**File:** `federation/models/player.py:132-141`

```python
def get_ranking(self, ranking='current_rating', players_objects=None):
    if players_objects is None:
        players_objects = self.get_actual_players_list()
    return players_objects.filter(**{
        ranking + "__gt" : getattr(self, ranking)
    }).count() + 1
```

This runs a COUNT query for every player displayed. On `/players/` with 100 players, that's 100+ additional queries just for ranking badges.

### 3. Statistics Page Is O(n*m) With DB Queries In Loop

**File:** `federation/views/statistics.py:53-128`

```python
for tournament in tournaments_all:  # n tournaments
    teams_count = int(tournament.get_teams_count())  # may query DB
    ...
    tournaments_data['countries'][...]['teams'] += tournament.get_teams().count()  # DB query per tournament
```

For a year with 50 tournaments, this generates 50-100+ queries plus significant Python computation.

### 4. No `select_related()` or `prefetch_related()` Anywhere

Searched the entire codebase — zero usages of either. Every foreign key access in templates triggers a separate query:

- `tournament.organizer_club` — extra query
- `tournament.main_organizer` — extra query
- `tournament.country` — extra query
- `player.current_club` — extra query
- `club.city.country` — two extra queries
- `team.players.all()` — extra query per team

### 5. `recalculate_ratings()` Is O(n*m) Per Player

**File:** `federation/models/player.py:159-243`

Each player's rating recalculation:
1. Fetches all past tournaments for that player
2. For each tournament, calls `get_team_which_contains_player()` (1+ queries)
3. Saves the player

For 200 players * 20 tournaments each = 4000+ queries per weekly cron run.

### 6. Tournament Protocol View Counts Players In Loop

**File:** `federation/views/tournaments.py:235-236`

```python
for team in teams:
    players_count += team.team.players.count()
```

Extra query per team. Could be a single aggregate.

### 7. Tournament CSV/JSON Export Queries Per Team

**File:** `federation/views/tournaments.py:129-210`

```python
for team in tournament.teams.all():
    for player in team.players.all():  # N+1
        if player.current_club is not None:  # extra query
```

## Missing Database Indexes

Based on query patterns observed, these fields should have `db_index=True`:

- `Player.is_licence_active` — filtered in ranking queries
- `Player.current_club` — filtered in club stats
- `Player.current_rating` — used in COUNT comparisons
- `Tournament.start_date` — filtered in nearly every tournament query
- `Tournament.category` — filtered in type queries
- `Tournament.is_goes_to_rating` — filtered frequently
- `Tournament.is_processing_finished` — status checks
- `TeamTournamentMembership.tournament` — FK, may already have index
- `TeamTournamentMembership.team` — FK lookups
- `PlayerDepartmentMembership.team` + `.player` — compound lookup

## Estimated Query Counts Per Page (No Instrumentation)

| Page | Estimated Queries | Notes |
|------|-------------------|-------|
| `/players/` (100 players) | 200-400 | ranking per player, club per player |
| `/clubs/` (20 clubs) | 80-150 | player counts, rating sums per club |
| `/tournament/<id>` (20 teams) | 60-100 | team players, power lookups |
| `/player/<id>` (10 past tournaments) | 30-60 | team lookups per tournament |
| `/statistics/` (50 tournaments) | 100-200 | teams count per tournament |

## Recommended Fixes (Priority Order)

### Phase 1: Quick Wins (High Impact, Low Risk)

1. Add `select_related()` to all view queries:
   ```python
   Tournament.objects.select_related('organizer_club', 'main_organizer', 'country')
   Player.objects.select_related('current_club', 'user')
   Club.objects.select_related('city', 'city__country', 'president')
   ```

2. Add `prefetch_related()` for M2M:
   ```python
   TeamTournamentMembership.objects.prefetch_related('team__players')
   ```

3. Add database indexes to frequently filtered fields.

### Phase 2: Template Filter Refactor (Medium Effort)

4. Move data preparation from template filters into view context:
   - Pre-compute club stats with annotations: `Club.objects.annotate(player_count=Count('player'))`
   - Pre-compute player rankings with window functions
   - Pre-fetch tournament membership data for player detail pages

5. Replace `rating_position()` with a pre-computed rank:
   ```python
   from django.db.models import Window, F
   from django.db.models.functions import Rank
   players.annotate(rank=Window(expression=Rank(), order_by=F('current_rating').desc()))
   ```

### Phase 3: Heavy Pages (Higher Effort)

6. Rewrite statistics view to use database aggregation:
   ```python
   Tournament.objects.filter(start_date__year=year).aggregate(...)
   Tournament.objects.values('country').annotate(count=Count('id'), teams=Sum('total_number_of_teams'))
   ```

7. Cache expensive public pages (statistics, player rankings) for 5-15 minutes.

8. Batch the weekly rating recalculation with `prefetch_related` and transaction management.

## Measurement Approach

Before optimizing, instrument:

1. Enable Django Debug Toolbar locally (or use `django-silk` which is already installed).
2. Measure query count on target pages.
3. Set baseline: "page X runs Y queries in Z ms."
4. After each fix, re-measure and document improvement.
5. Add query-count assertions in smoke tests for the worst pages.
