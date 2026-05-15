# Task 007: Performance Quick Wins

## Goal

Reduce database query volume by 50-80% on heavy pages with minimal code changes and low risk.

## Why This Matters

The app currently has zero `select_related()`/`prefetch_related()` usage. Every foreign key access in templates triggers an additional query. Pages like `/players/` and `/clubs/` execute hundreds of unnecessary queries.

## Scope

### 1. Add `select_related()` To View Queries

**Players views** (`views/players.py`):
```python
Player.objects.all().select_related('current_club', 'current_club__city', 'user')
```

**Clubs views** (`views/clubs.py`):
```python
Club.objects.all().select_related('city', 'city__country', 'president')
```

**Tournament views** (`views/tournaments.py`):
```python
Tournament.objects.select_related('organizer_club', 'main_organizer', 'country')
TeamTournamentMembership.objects.filter(...).select_related('team', 'tournament')
```

### 2. Add `prefetch_related()` For M2M

**Tournament detail/export** (`views/tournaments.py`):
```python
teams = TeamTournamentMembership.objects.filter(tournament=tournament).select_related('team').prefetch_related('team__players', 'team__players__current_club')
```

### 3. Add Database Indexes

Add `db_index=True` to frequently filtered fields (requires migration):
- `Player.is_licence_active`
- `Player.current_rating`
- `Tournament.start_date`
- `Tournament.is_goes_to_rating`
- `Tournament.is_processing_finished`

### 4. Optimize `get_list()` Classmethod

**File:** `models/tournament.py` — `get_list()` and `get_list_by_player()`

Add `select_related` to the base queryset returned by these methods.

### 5. Tournament Protocol View

**File:** `views/tournaments.py:234-236`

Replace loop-based player count:
```python
# Before
for team in teams:
    players_count += team.team.players.count()

# After
from django.db.models import Count
players_count = teams.aggregate(total=Count('team__players'))['total'] or 0
```

### 6. Club Stats Pre-computation (Quick Version)

For the clubs list page, use annotations instead of template filter queries:
```python
from django.db.models import Count, Sum, Avg
clubs = Club.objects.annotate(
    player_count=Count('player', filter=Q(player__is_licence_active=True)),
    total_rating=Sum('player__current_rating', filter=Q(player__is_licence_active=True)),
).select_related('city', 'city__country', 'president')
```

Pass these annotated values to the template instead of calling `get_number_of_players`, `get_club_rating_points`, `get_club_avg_rating_points` filters.

## Acceptance Criteria

- `/players/` page query count reduced from ~200-400 to <50
- `/clubs/` page query count reduced from ~80-150 to <20
- `/tournament/<id>` page query count reduced from ~60-100 to <20
- No behavior changes visible to users
- Smoke tests pass
- Measured with Django Debug Toolbar or Silk before/after

## Technical Notes

- `select_related` for FK/OneToOne (generates JOIN)
- `prefetch_related` for M2M/reverse FK (generates separate IN query)
- Database indexes are backwards-compatible (additive migration)
- Annotation approach for clubs may require adjusting template to use `{{ item.player_count }}` instead of `{{ item|get_number_of_players }}`

## Complexity

M

## Risk

Low — these are additive optimizations that don't change logic.

## Big Win

High — dramatic reduction in page load time for the most-visited pages.
