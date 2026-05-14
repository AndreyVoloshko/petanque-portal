# Found Bugs And Correctness Risks

## Summary

These are concrete bugs found during static inspection. Some are actively exploitable, others manifest only with certain data states. Ordered by impact.

## Critical Bugs (Security + Data Integrity)

### 1. Tournament `meta` Can Be Updated Without Auth

**File:** `federation/views/tournaments.py:36-39`

Any POST containing `meta` updates the tournament before authentication/authorization checks run.

```python
if 'meta' in request.POST:
    tournament.meta = request.POST['meta']
    tournament.save()
    return JsonResponse({'status': 'ok'}, safe=False)
```

Impact: unauthorized data mutation by anonymous users.

### 2. Tournament View Is CSRF-Exempt

**File:** `federation/views/tournaments.py:29`

All state-changing operations (meta update, team deletion, placement edits) bypass Django CSRF protection.

### 3. Error Handlers Crash On Django 5.x

**File:** `federation/urls.py:82-90`

```python
def handler404(request):
    response = render(request, '404.html', {},
                      context_instance=RequestContext(request))
```

`context_instance` parameter was removed in Django 2.0. These handlers will raise `TypeError` if invoked, meaning 404/500 errors produce additional 500 errors.

Impact: no custom error pages work; users see Django's default error response or a traceback in DEBUG mode.

## High-Impact Bugs

### 4. Statistics Page Divide-By-Zero

**File:** `federation/views/statistics.py:144,151`

```python
tournaments_data['ua_avg_teams_count'] = int(sum(tournaments_data['ua_teams_count']) / len(tournaments_data['ua_teams_count']))
```

No zero check for `ua_teams_count` or `ua_players_count`. If there are no Ukrainian tournaments for a year/period, the page crashes with `ZeroDivisionError`.

The foreign equivalents (lines 146-148, 153-156) have the check, but Ukrainian ones don't.

### 5. `date_filter.is_integer()` Called On String

**File:** `federation/models/tournament.py:371,422`

```python
elif date_filter and date_filter.is_integer():
```

`date_filter` is a URL path segment (string). Strings don't have `is_integer()` — they have `isdigit()`. This will raise `AttributeError` for any non-standard date filter value.

Impact: URLs like `/tournaments/2024/` crash with 500.

### 6. Duplicate Dictionary Key In Player Summary

**File:** `federation/views/players.py:56-58`

```python
player_summary_info = {
    'this_year_tournaments_count': this_year_tournaments_count,
    ...
    'this_year_tournaments_count': this_year_liga_tournaments_count,  # overwrites!
    ...
}
```

The total tournament count is overwritten by the league tournament count.

Impact: player detail page shows wrong statistic.

### 7. Team Power Division By Zero

**File:** `federation/models/tournament.py:490`

```python
power = power / self.team.players.count()
```

If a team has zero players (e.g., race condition during registration, data cleanup), this crashes.

Impact: rating recalculation fails for the entire tournament.

### 8. Department Template Filters Index Empty QuerySets

**File:** `federation/templatetags/app_filters.py:706-728`

```python
def get_role_in_department(player, department):
    department_role = PlayerDepartmentMembership.objects.filter(team=department, player=player)
    if not department_role[0]:  # IndexError if queryset is empty
```

Three filters (`get_role_in_department`, `get_description_in_department`, `get_order_in_department`) all use `[0]` on a queryset that may be empty.

Impact: departments page crashes if a player-department relation is missing.

### 9. Registration Form `Player.objects.get()` Without Exception Handling

**File:** `federation/forms/registration_team_form.py:75`

```python
player = Player.objects.get(pk=player_id)
if not player:  # This check is unreachable — get() either returns or raises
```

If a player ID doesn't exist, `Player.DoesNotExist` is raised. The `if not player` check never executes because `get()` never returns a falsy value.

Impact: invalid player IDs produce a 500 error instead of a form validation error.

### 10. File Upload Validation Method Never Called

**File:** `federation/forms/player_form.py`

`clean_content()` validates upload, but the form field is named `avatar`, not `content`. Django will never call `clean_content()` for a field that doesn't exist.

Impact: avatar uploads have no size/type validation beyond what S3 accepts.

## Medium-Impact Bugs

### 11. `team_place_in_tournament` Crashes When place_max Is None

**File:** `federation/templatetags/app_filters.py:433`

```python
if team.place_max > 0:
```

If `place_max` is None (nullable in schema?), this raises `TypeError: '>' not supported between instances of 'NoneType' and 'int'`.

### 12. Tournament JSON Export Has Duplicate Key

**File:** `federation/views/tournaments.py:177-178`

```python
current_team = {
    'power': team.power,
    ...
    'power': team.power,  # duplicate key
```

The `power` key appears twice. Only cosmetic (same value), but indicates copy-paste error.

### 13. CSV Export Transliteration May Fail

**File:** `federation/views/tournaments.py:259`

```python
tmp.append(translit(item, 'ru', reversed=True).encode("utf-8").decode("utf-8"))
```

The `translit()` function can raise if it encounters characters it cannot handle. No exception handling exists.

### 14. Statistics Page Accumulates Teams Count Differently Than Expected

**File:** `federation/views/statistics.py:91`

```python
tournaments_data['countries'][tournament.country.code]['teams'] += tournament.get_teams().count()
```

`get_teams()` returns `TeamTournamentMembership.objects.filter(tournament=self)` — this hits the DB per tournament. On the same page, `get_teams_count()` is also called (which may use `total_number_of_teams` field instead), creating inconsistent counts.

### 15. Player `get_by_name_and_surname` Catches Wrong Exception

**File:** `federation/models/player.py:252-263`

```python
try:
    player = Player.objects.get(name__iexact=name, surname__iexact=surname)
    if player:
        return player
    player = Player.objects.get(name__iexact=surname, surname__iexact=name)
except Exception:
    player = None
```

If the first `get()` returns a player (it always does when it doesn't raise), the function returns. The second `get()` (name/surname swap) is unreachable. Also, `except Exception` masks `MultipleObjectsReturned`.

### 16. Cron Job Timing

**File:** `components/web-api/conf/crontab.txt`

```
0 0 * * 3 root cd /application && python manage_cron.py recalculate_ratings
```

Runs at midnight UTC on Wednesdays. The `manage_cron.py` file correctly loads environment from PID 1, but there's no monitoring or alerting if it fails.

## Low-Impact Issues

### 17. Unused Import: `from django.template import RequestContext`

**File:** `federation/urls.py:2`

Imported but only used in broken error handlers.

### 18. `from django.http import *` Wildcard Import

**File:** `federation/views/login.py:2`

Pollutes namespace; non-idiomatic.

## Recommendation

Fix in phases:
1. Security-impacting bugs (#1, #2, #3) — immediate
2. Crash bugs (#4, #5, #6, #7, #8, #9) — before any refactoring
3. Correctness issues (#10-#16) — alongside related feature work
