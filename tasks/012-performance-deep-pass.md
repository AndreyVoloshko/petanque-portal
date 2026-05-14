# Task 012: Performance Deep Pass

## Goal

Move remaining DB-heavy logic out of template filters and into views, and rewrite the statistics page with database aggregation.

## Prerequisites

- Task 007 (Performance Quick Wins) completed
- Task 005 (Smoke Tests) in place to verify no regressions

## Scope

### 1. Move Template Filter Queries Into Views

Replace filters that query the DB with pre-computed context data:

**Player detail page:**
- `team_short_name_in_tournament` → pre-fetch all player's team memberships
- `team_rating_points_in_tournament` → include in prefetched data
- `team_power_in_tournament` → include in prefetched data
- `team_place_in_tournament` → include in prefetched data
- `player_national_teams` → prefetch in view
- `player_records` → prefetch in view
- `is_tournament_in_player_rating` → pre-compute in view

**Players list page:**
- `rating_position` → pre-compute rankings with window function or cached rank

**Clubs page:**
- Already handled in Task 007 with annotations

### 2. Replace `rating_position` With Pre-computed Rank

Current: `COUNT(*) WHERE rating > my_rating` per player (O(n) per player)

Replace with:
```python
from django.db.models import Window
from django.db.models.functions import Rank

players = Player.objects.annotate(
    rank=Window(expression=Rank(), order_by=F('current_rating').desc())
)
```

Or use a stored/cached ranking field updated during rating recalculation.

### 3. Rewrite Statistics View With Aggregation

Replace Python loops over all tournaments with DB-level aggregation:

```python
from django.db.models import Count, Sum, Avg, Q, F

# Countries breakdown
countries = Tournament.objects.filter(...).values('country').annotate(
    count=Count('id'),
    teams_total=Sum('total_number_of_teams')
)

# Average teams
averages = Tournament.objects.filter(
    country=settings.CURRENT_COUNTRY
).aggregate(
    avg_teams=Avg('total_number_of_teams')
)
```

### 4. Optimize Weekly Rating Recalculation

Current: per-player sequential processing with N+1 queries inside each player.

Improve:
- Prefetch all tournament memberships for all licensed players in one query
- Process in batches with `select_related`
- Wrap in a transaction for atomicity
- Add progress logging

### 5. Add Query Count Tests

For the worst pages, add test assertions:
```python
def test_players_list_query_count(client, django_assert_num_queries):
    # Create 20 players
    with django_assert_num_queries(10):  # max acceptable queries
        response = client.get('/players/')
```

## Acceptance Criteria

- Template filters no longer execute DB queries (only format pre-loaded data)
- Statistics page uses aggregation, not Python loops
- Players list page < 15 queries regardless of player count
- Weekly rating recalculation completes in < 5 minutes for 500 players
- All pages render identical results

## Complexity

L

## Risk

Medium — template filter refactoring requires changing how views prepare data and how templates consume it.

## Big Win

High — eliminates the remaining N+1 patterns and makes the app responsive under load.
