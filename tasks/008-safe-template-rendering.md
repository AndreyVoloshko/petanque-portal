# Task 008: Safe Template Rendering

## Goal

Eliminate stored XSS risk by converting string-concatenated HTML in template filters to Django's safe HTML utilities.

## Why This Matters

There are 178 uses of `|safe` in templates, and many custom filters in `app_filters.py` build HTML via string concatenation with database values. If any admin-editable field (social URLs, player names, club names, tournament places) contains JavaScript, it executes in visitors' browsers.

## Scope

### Priority 1: Filters That Include User-Editable URLs/Text

1. **`social_field()`** (line 154-166) — builds `<a href="VALUE">` where VALUE is from club.facebook/twitter/website/instagram
   - Convert to `format_html('<a target="_blank" href="{}"...', value)`

2. **`user_profile_link()`** (line 108-116) — includes player name in HTML
   - Convert to `format_html()`

3. **`tournament_field()`** (line 346-381) — renders arbitrary field values as HTML
   - Convert string building to `format_html()` with explicit field escaping

4. **`club_logo()`** (line 68-80) — builds `<img>` and `<a>` with URL
   - Already partly safe (URLs from settings/model ID), convert to `format_html()`

### Priority 2: Filters That Build Static HTML With Model Data

5. **`country_icon()`** / **`country_flag()`** (lines 53-64) — uses `country.code` and `country.name`
6. **`licence_number()`** (line 221)
7. **`gender()`** (line 209)
8. **`player_age_category()`** / **`season_player_age_category()`** (lines 169-206)
9. **`arbiter_label()`** / **`coach_label()`** / **`player_sport_title_label()`** (lines 238-291)
10. **`player_national_teams()`** / **`player_records()`** (lines 295-342)
11. **`tournament_status()`** / **`tournament_protocol()`** (lines 563-607)
12. **`tournament_registration_tab()`** (line 691-701)

### Priority 3: Remove Unnecessary `|safe` From Templates

Many templates apply `|safe` to filters that return simple strings (numbers, text). Remove `|safe` where the filter output is just text, not HTML.

Example: `{{ item|rating_points:rating_field|safe }}` — `rating_points` returns `str(value)`, no HTML. Remove `|safe`.

### Conversion Pattern

Before:
```python
def social_field(item, field):
    value = getattr(item, field)
    return '<a target="_blank" href="' + value + '"...'
```

After:
```python
from django.utils.html import format_html

def social_field(item, field):
    value = getattr(item, field)
    if not value:
        return ''
    return format_html(
        '<a target="_blank" href="{}" ...><i class="bi bi-{}"></i></a>',
        value, icon_class_name
    )
```

When using `format_html()`, Django auto-escapes the `{}` parameters, so XSS through DB values becomes impossible.

### Template Changes

For filters that now return `format_html()` results, the template `|safe` filter becomes unnecessary (format_html marks output as safe). However, removing `|safe` from templates can be done gradually — format_html output passes through `|safe` safely.

## Acceptance Criteria

- All filters that include user-editable data use `format_html()` or `format_html_join()`
- XSS payload in a social URL field (e.g., `javascript:alert(1)`) is escaped in output
- Pages render identically for normal data (visual regression check)
- Template `|safe` count reduced from 178 to < 50 (filters returning plain text)

## Complexity

L — 20+ filters to modify, many templates to verify.

## Risk

Medium — visual regressions possible if escaping changes rendered output. Mitigate with before/after screenshots of key pages.

## Big Win

High — eliminates an entire class of vulnerabilities.
