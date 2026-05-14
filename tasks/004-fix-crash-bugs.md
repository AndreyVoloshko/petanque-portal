# Task 004: Fix Crash Bugs

## Goal

Fix concrete bugs that cause 500 errors on public pages under certain data conditions.

## Why This Matters

These bugs crash pages for real users. Several are triggered by empty data states that occur naturally (new season, new federation, filtered views with no results).

## Scope

### 1. Statistics Page Divide-By-Zero

**File:** `federation/views/statistics.py:144,151`

Fix: add zero-length check for `ua_teams_count` and `ua_players_count` (same pattern already used for foreign equivalents).

```python
if len(tournaments_data['ua_teams_count']) > 0:
    tournaments_data['ua_avg_teams_count'] = int(sum(tournaments_data['ua_teams_count']) / len(tournaments_data['ua_teams_count']))
else:
    tournaments_data['ua_avg_teams_count'] = 0
```

### 2. `date_filter.is_integer()` → `date_filter.isdigit()`

**File:** `federation/models/tournament.py:371,422`

Replace `date_filter.is_integer()` (AttributeError on strings) with `date_filter.isdigit()`.

### 3. Department Filters Empty QuerySet Indexing

**File:** `federation/templatetags/app_filters.py:706-728`

Replace `department_role[0]` with `.first()`:
```python
def get_role_in_department(player, department):
    membership = PlayerDepartmentMembership.objects.filter(team=department, player=player).first()
    if not membership:
        return ''
    return membership.role
```

### 4. Team Power Division By Zero

**File:** `federation/models/tournament.py:490`

Add guard:
```python
player_count = self.team.players.count()
if player_count == 0:
    self.power = 0
    self.save()
    return
power = power / player_count
```

### 5. Registration Form `Player.DoesNotExist`

**File:** `federation/forms/registration_team_form.py:74-78`

Replace `Player.objects.get()` with proper exception handling:
```python
try:
    player = Player.objects.get(pk=player_id)
except Player.DoesNotExist:
    self._errors['no_player'] = 'Гравець з номером '+str(player_id)+' не існує'
    return False
```

### 6. Error Handlers Use Removed API

**File:** `federation/urls.py:82-90`

Replace deprecated handlers:
```python
def handler404(request, exception=None):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)
```

Remove unused `RequestContext` import.

### 7. Duplicate Dictionary Key

**File:** `federation/views/players.py:56-58`

Rename second key to `this_year_liga_tournaments_count`:
```python
player_summary_info = {
    'this_year_tournaments_count': this_year_tournaments_count,
    'this_year_b_tournaments_count': this_year_b_tournaments_count,
    'this_year_liga_tournaments_count': this_year_liga_tournaments_count,
    ...
}
```

### 8. File Upload Validation (`clean_content` → `clean_avatar`)

**File:** `federation/forms/player_form.py`

Rename `clean_content()` to `clean_avatar()` so Django calls it for the `avatar` field.

### 9. Player `get_by_name_and_surname` Logic Error

**File:** `federation/models/player.py:252-263`

The second `get()` (name/surname swap) is unreachable. Fix:
```python
@classmethod
def get_by_name_and_surname(cls, name, surname):
    try:
        return Player.objects.get(name__iexact=name, surname__iexact=surname)
    except Player.DoesNotExist:
        pass
    try:
        return Player.objects.get(name__iexact=surname, surname__iexact=name)
    except Player.DoesNotExist:
        return None
```

## Acceptance Criteria

- Statistics page loads without crash when no tournaments exist for selected period
- `/tournaments/2024/` resolves without AttributeError
- Departments page renders even with incomplete membership data
- Team registration handles invalid player IDs with user-friendly error
- Power recalculation handles empty teams gracefully
- Custom 404/500 pages render on Django 5.x
- Player detail page shows correct tournament counts

## Complexity

M

## Risk

Medium — each fix is small and isolated, but touching many files increases chance of typos.

## Big Win

High — eliminates visible crashes for end users.
