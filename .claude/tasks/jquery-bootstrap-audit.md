# jQuery and Bootstrap Audit

Generated: 2026-06-02

Scope: `components/web-api/application`, excluding `RTK.md` and minified vendor files unless explicitly noted.

## Executive Summary

Complete jQuery removal is realistic, but it is blocked by plugin dependencies, not by simple DOM code. The hard blockers are DataTables, jQuery UI autocomplete/datepicker, and Select2. Most other jQuery call sites are small and can be rewritten with `querySelector`, `addEventListener`, `fetch`, and Bootstrap 5's native JS API.

Complete Bootstrap removal is possible but much larger. Bootstrap CSS is embedded across almost the whole template layer and in generated HTML from Python template filters and Crispy Forms. Removing Bootstrap JS is a finite task. Removing Bootstrap CSS is a frontend rewrite.

Recommended sequence:

1. Add template blocks for page-specific CSS and JS.
2. Move DataTables, jQuery UI, and Select2 off the global head and load them only where needed.
3. Replace jQuery UI search and datepicker, then remove jQuery UI globally.
4. Replace simple jQuery snippets and Bootstrap jQuery-style calls.
5. Replace or remove DataTables and Select2.
6. Remove jQuery.
7. Treat Bootstrap CSS removal as a separate design-system migration.

## Current Global Includes

All pages include `components/web-api/application/federation/templates/common/head.html`.

| Lines | Asset | Scope | Notes |
| --- | --- | --- | --- |
| 24 | `{% static 'bootstrap-theme.css' %}` | Global CSS | Local build that contains Start Bootstrap Stylish Portfolio and Bootstrap 5.2.3. |
| 32 | Bootstrap Icons CSS CDN | Global CSS/font | Icons are used in many templates and filters. Font files are additional network requests. |
| 35 | Bootstrap 5.3.2 bundle CDN | Global JS | Enables dropdown, collapse, tab, tooltip, alert dismiss, etc. |
| 38 | jQuery 3.6.0 CDN | Global JS | Required by jQuery UI, DataTables 1.x, Select2, and local snippets. |
| 41, 43 | jQuery UI CSS/JS CDN | Global CSS/JS | Used by global search autocomplete and player registration datepicker. |
| 46, 49, 50 | DataTables Bootstrap 5 CSS/JS CDN | Global CSS/JS | Used by six table partials, but loaded on every page. |
| 54, 58 | FullCalendar CSS/JS CDN | Global CSS/JS | Calendar JS is only needed on the calendar page. The CSS URL returned 404 during this audit. |
| 56 | `{% static 'style-v2.css' %}` | Global CSS | Custom portal CSS. |

`common/head.html` also defines DataTables custom ordering and a `.force-follow-link` click handler at lines 61-81.

## Asset Weight

Sizes measured on 2026-06-02 with raw bytes and gzip response bytes. CDN values can change if a provider changes compression or asset metadata.

### Local Static Assets

| Asset | Raw | Gzip | Brotli | Loaded? |
| --- | ---: | ---: | ---: | --- |
| `static/bootstrap-theme.css` | 242,873 | 30,642 | 22,388 | Yes, globally |
| `static/style-v2.css` | 127,403 | 20,055 | 16,574 | Yes, globally |
| `static/style.css` | 4,724 | 1,405 | 1,117 | Not found in templates |
| `static/dataTables.bootstrap.css` | 8,850 | 1,959 | 1,623 | Not found in templates |
| `static/dataTables.bootstrap.js` | 4,849 | 1,992 | 1,634 | Not found in templates |
| `static/jquery.dataTables.js` | 81,906 | 27,853 | 24,831 | Not found in templates |
| `static/scripts.js` | 945 | 407 | 308 | Not found in templates |

Note: the local `dataTables.bootstrap.js` is a Bootstrap 3 integration, while the global template loads DataTables Bootstrap 5 from CDN. The local DataTables files appear stale or unused.

### CDN Assets

| Asset | Raw | Gzip response | Scope |
| --- | ---: | ---: | --- |
| Bootstrap 5.3.2 bundle JS | 80,663 | 23,841 | Global |
| Bootstrap Icons CSS | 99,556 | 14,293 | Global, plus font files |
| jQuery 3.6.0 JS | 89,501 | 30,963 | Global |
| jQuery UI 1.13.2 CSS | 31,340 | 7,650 | Global |
| jQuery UI 1.13.2 JS | 255,084 | 67,865 | Global |
| DataTables Bootstrap 5 CSS | 11,981 | 2,113 | Global |
| DataTables jQuery JS | 87,103 | 29,824 | Global |
| DataTables Bootstrap 5 JS | 2,358 | 1,196 | Global |
| Select2 CSS | 15,275 | 1,998 | Team registration only |
| Select2 JS | 67,751 | 19,360 | Team registration only |
| FullCalendar JS | 282,117 | 81,171 | Global, used by calendar page |
| flag-icon CSS | 33,481 | 2,449 | Global |

The global jQuery-related payload is about 140 KB gzip before Select2. The largest jQuery blocker is jQuery UI, not jQuery core.

## jQuery Usage Inventory

Direct app-authored jQuery usage appears in 27 files. Vendor files are excluded here.

| File | Usage | Replacement Direction |
| --- | --- | --- |
| `templates/common/head.html` | Global jQuery include, DataTables custom sort extension, `.force-follow-link` click handler. | Move DataTables extension to DataTables-only asset block. Replace click handler with native delegated listener. |
| `templates/common/menu.html` | `$(function)`, jQuery UI `autocomplete`, `$.ajax`, `$.map`, DOM creation, theme toggle. | Replace autocomplete with native custom combobox using `fetch`; replace theme toggle with `document.documentElement.dataset.bsTheme`. |
| `templates/common/header.html` | GDPR button click handlers and `fadeOut().remove()`. | Native `addEventListener`; CSS transition or immediate `remove()`. |
| `templates/documents/documents.html` | Tab click calls `$(this).tab('show')`. | Use `bootstrap.Tab.getOrCreateInstance(element).show()` or rely on `data-bs-toggle`. |
| `templates/tournaments/tournament.html` | Tab click calls `$(this).tab('show')`. | Same as above. |
| `templates/arbiters/arbiters.html` | Tooltip init, tab click, card sorting with jQuery traversal. | Native tooltip helper, native tabs, `Array.from(...).sort()` and `append`. |
| `templates/coaches/coaches.html` | Same pattern as arbiters. | Same replacement. |
| `templates/departments/departments.html` | Same pattern as arbiters. | Same replacement. |
| `templates/sport_titles/sport_titles.html` | Same pattern as arbiters. | Same replacement. |
| `templates/clubs/clubs_cards.html` | Sort club cards by `data-rating`, initialize tooltips. | Native sort and shared tooltip helper. |
| `templates/clubs/clubs_table.html` | DataTables init and tooltip init. | Replace DataTables or load DataTables only for this partial; use native tooltip helper. |
| `templates/main_page.html` | Tooltip init with jQuery fallback. | Native tooltip helper. |
| `templates/main_page/tournaments_list.html` | Tooltip init. | Native tooltip helper. |
| `templates/national_teams/current_team.html` | Tooltip init and card sorting. | Native tooltip helper and native sorting. |
| `templates/players/player.html` | Tooltip fallback with `window.jQuery`. | Remove fallback after Bootstrap native helper exists. |
| `templates/players/players_cards.html` | Sort player cards, tooltip init. | Native sorting and tooltip helper. |
| `templates/players/players_table.html` | Tooltip fallback, delegated row click, `.data()`, click preventer. | Mostly already native; replace remaining jQuery with delegated `addEventListener` and `dataset.href`. |
| `templates/register/player.html` | jQuery UI datepicker, show/hide country-specific fields. | Use native `input[type=date]`, or a non-jQuery picker; replace show/hide with `hidden`/class toggles. |
| `templates/register/team.html` | Select2 include and `.select2({ ajax })`. | Replace Select2 with Tom Select, Slim Select, Choices.js, or a custom async combobox. |
| `templates/seasons/players_list.html` | DataTables, column filters, redraw tooltip reinit. | Replace DataTables or isolate it to this page; native tooltip helper on redraw if DataTables remains. |
| `templates/tournaments/calendar.html` | `$(document).ready`, `$.ajax` for FullCalendar events. | Use `DOMContentLoaded` and `fetch`. |
| `templates/tournaments/player_future_tournaments.html` | DataTables and tooltip init. | Replace or isolate DataTables; native tooltip helper. |
| `templates/tournaments/player_past_away_tournaments.html` | DataTables and tooltip init. | Replace or isolate DataTables; native tooltip helper. |
| `templates/tournaments/player_past_tournaments.html` | DataTables and tooltip init. | Replace or isolate DataTables; native tooltip helper. |
| `templates/tournaments/tournament_teams.html` | DataTables, tooltip redraw handling, save places `$.ajax`, `serializeArray`. | Replace or isolate DataTables; use `fetch`, `FormData`, and native serialization. |
| `templates/tournaments/tournaments.html` | Native tooltip path with jQuery fallback. | Remove fallback after jQuery migration. |
| `static/scripts.js` | Login/register form toggles, tooltip init, tab init. | File appears unused. Remove if confirmed, or rewrite and include intentionally. |

## jQuery Plugin Blockers

| Plugin | Files | Current Reason | Removal Option |
| --- | --- | --- | --- |
| DataTables | `clubs/clubs_table.html`, `seasons/players_list.html`, `tournaments/player_future_tournaments.html`, `tournaments/player_past_away_tournaments.html`, `tournaments/player_past_tournaments.html`, `tournaments/tournament_teams.html` | Sorting, paging, search, length menu, column filtering, redraw events. | Prefer server-side sorting/pagination for portal tables, or use a non-jQuery grid. If keeping DataTables, load it only on these pages. |
| jQuery UI Autocomplete | `common/menu.html` | Global search autocomplete. | Custom async combobox with `fetch` and ARIA listbox. This is the key to removing jQuery UI globally. |
| jQuery UI Datepicker | `register/player.html` | Player birth/date field. | Native date input if acceptable, or a small non-jQuery picker. |
| Select2 | `register/team.html` | Async player select for team registration. | Tom Select, Slim Select, Choices.js, or custom async select. This file already loads Select2 page-locally. |
| Bootstrap jQuery facade | 21 files call `.tooltip()` or `.tab()`. | Bootstrap behavior invoked through jQuery syntax. | Use Bootstrap 5 native classes: `bootstrap.Tooltip`, `bootstrap.Tab`, etc. |

## Bootstrap Usage Inventory

Bootstrap is heavily used.

Summary:

- 64 of 76 template files contain Bootstrap-like class tokens.
- `federation/templatetags/app_filters.py` emits Bootstrap classes and attributes.
- `crispy_bootstrap5` is installed and configured in `api/settings.py`.
- Python forms and views explicitly set Bootstrap classes such as `form-control` and `btn btn-success`.
- Bootstrap behavior attributes found: 86 `data-bs-toggle="tooltip"`, 11 `data-bs-toggle="tab"`, 4 `data-bs-toggle="pill"`, 5 `data-bs-toggle="dropdown"`, 4 `data-bs-toggle="collapse"`.
- Legacy Bootstrap attributes found: 8 `data-toggle="tooltip"` plus older `data-placement`, `data-original-title`, and one carousel `data-target`.

### Bootstrap CSS Dependency Files

These files contain Bootstrap class tokens and would need review before removing Bootstrap CSS:

| File | Match count |
| --- | ---: |
| `templates/404.html` | 8 |
| `templates/500.html` | 8 |
| `templates/arbiters/arbiters.html` | 21 |
| `templates/clubs/club.html` | 1 |
| `templates/clubs/club_info_panel.html` | 23 |
| `templates/clubs/club_short_info_panel.html` | 16 |
| `templates/clubs/clubs.html` | 11 |
| `templates/clubs/clubs_cards.html` | 22 |
| `templates/clubs/clubs_table.html` | 22 |
| `templates/clubs/grid_item_club.html` | 22 |
| `templates/coaches/coaches.html` | 21 |
| `templates/common/footer.html` | 5 |
| `templates/common/grid_page.html` | 2 |
| `templates/common/head.html` | 1 |
| `templates/common/menu.html` | 64 |
| `templates/common/messages.html` | 2 |
| `templates/common/page_base.html` | 1 |
| `templates/common/page_with_header.html` | 2 |
| `templates/common/table_page.html` | 1 |
| `templates/departments/departments.html` | 22 |
| `templates/documents/documents.html` | 15 |
| `templates/email_confirm/invalid.html` | 5 |
| `templates/email_confirm/prompt.html` | 10 |
| `templates/email_confirm/success.html` | 5 |
| `templates/forms/profile/image_field.html` | 6 |
| `templates/login.html` | 13 |
| `templates/main_page.html` | 11 |
| `templates/main_page/players_list.html` | 4 |
| `templates/main_page/tournaments_list.html` | 27 |
| `templates/national_teams/current_team.html` | 14 |
| `templates/national_teams/national_teams.html` | 3 |
| `templates/national_teams/national_teams_list.html` | 3 |
| `templates/password_reset/complete.html` | 5 |
| `templates/password_reset/confirm.html` | 11 |
| `templates/password_reset/done.html` | 5 |
| `templates/password_reset/request.html` | 8 |
| `templates/players/_player_rating_card.html` | 25 |
| `templates/players/player.html` | 47 |
| `templates/players/player_info_panel.html` | 32 |
| `templates/players/player_seasons.html` | 6 |
| `templates/players/player_short_info_panel.html` | 18 |
| `templates/players/player_statistic_and_records_info_panel.html` | 6 |
| `templates/players/players_cards.html` | 18 |
| `templates/players/players_table.html` | 17 |
| `templates/profile.html` | 9 |
| `templates/records/records_table.html` | 19 |
| `templates/register/player.html` | 10 |
| `templates/register/team.html` | 16 |
| `templates/seasons/players_list.html` | 17 |
| `templates/seasons/seasons_list.html` | 2 |
| `templates/sport_titles/sport_titles.html` | 21 |
| `templates/statistics/statistics.html` | 33 |
| `templates/tournaments/calendar.html` | 4 |
| `templates/tournaments/player_future_tournaments.html` | 12 |
| `templates/tournaments/player_past_away_tournaments.html` | 13 |
| `templates/tournaments/player_past_tournaments.html` | 17 |
| `templates/tournaments/pure_teams_list.html` | 10 |
| `templates/tournaments/tournament.html` | 16 |
| `templates/tournaments/tournament_delegations.html` | 12 |
| `templates/tournaments/tournament_protocol.html` | 15 |
| `templates/tournaments/tournament_summary.html` | 20 |
| `templates/tournaments/tournament_teams.html` | 9 |
| `templates/tournaments/tournaments.html` | 1 |
| `templates/tournaments/tournaments_table.html` | 14 |
| `templatetags/app_filters.py` | 39 |

Most common Bootstrap class families found: grid/layout (`row`, `col-*`, `container`), cards, tables, nav/dropdown, buttons, badges, alerts, form controls, pagination, spacing utilities, text/background utilities, and flex utilities.

### Bootstrap JS Behavior Files

| Behavior | Files | Replacement If Removing Bootstrap JS |
| --- | --- | --- |
| Tooltips | `arbiters/arbiters.html`, `clubs/club_short_info_panel.html`, `clubs/clubs_cards.html`, `clubs/clubs_table.html`, `coaches/coaches.html`, `departments/departments.html`, `main_page.html`, `main_page/tournaments_list.html`, `national_teams/current_team.html`, `players/_player_rating_card.html`, `players/player.html`, `players/player_seasons.html`, `players/player_short_info_panel.html`, `players/players.html`, `players/players_cards.html`, `players/players_table.html`, `seasons/players_list.html`, `seasons/seasons.html`, `sport_titles/sport_titles.html`, `tournaments/player_future_tournaments.html`, `tournaments/player_past_away_tournaments.html`, `tournaments/player_past_tournaments.html`, `tournaments/pure_teams_list.html`, `tournaments/tournament_summary.html`, `tournaments/tournament_teams.html`, `tournaments/tournaments.html`, `tournaments/tournaments_table.html`, `templatetags/app_filters.py` | Native `title` only for simple cases, or custom tooltip component for styled/interactive behavior. |
| Tabs and pills | `arbiters/arbiters.html`, `clubs/clubs.html`, `coaches/coaches.html`, `departments/departments.html`, `documents/documents.html`, `main_page.html`, `profile.html`, `sport_titles/sport_titles.html`, `tournaments/tournament.html`, `static/scripts.js` | Custom tab controller toggling `active`, `show`, `hidden`, `aria-selected`, and focus state. |
| Dropdowns | `common/menu.html`, `tournaments/tournament_summary.html` | Custom menu button behavior with keyboard support and outside-click close. |
| Collapse | `common/menu.html`, `players/player.html` | Custom disclosure controller toggling height/visibility and `aria-expanded`. |
| Alert dismiss | `common/messages.html` | Native click handler that removes the alert node. |
| Carousel legacy attributes | `django_bootstrap_carousel/carousel.html` | Update to Bootstrap 5 attributes or replace with custom carousel if used. |

## Bootstrap Version and Legacy Issues

- CSS bundle: local `bootstrap-theme.css` contains Bootstrap 5.2.3 and Start Bootstrap Stylish Portfolio 6.0.6.
- JS bundle: CDN Bootstrap 5.3.2.
- DataTables integration: CDN Bootstrap 5 integration, but local unused files include a Bootstrap 3 DataTables integration.
- Legacy attributes still exist:
  - `data-toggle="tooltip"` in `app_filters.py`, `pure_teams_list.html`, `player_seasons.html`, and `static/scripts.js`.
  - `data-placement`, `data-original-title`, and `data-html` in older tooltip markup.
  - `data-target` / `data-slide-to` in `django_bootstrap_carousel/carousel.html`.
- `btn-xs` appears in legacy templates. Bootstrap 5 does not define `btn-xs`.

Normalize these before a larger Bootstrap migration.

## Replacement Plan

### Phase 1: Prepare the Template System

Add optional blocks to the base templates:

- `extra_css` in `common/head.html`.
- `extra_js` before `</body>` in `common/foot.html`.

Then move page-specific libraries out of `common/head.html`:

- DataTables CSS/JS only on the six DataTables partial/page owners.
- jQuery UI only while `common/menu.html` or `register/player.html` still need it.
- FullCalendar only on `tournaments/calendar.html`.

This phase reduces global payload without changing behavior.

### Phase 2: Remove Easy jQuery

Replace simple patterns:

```js
$(document).ready(init)
```

with:

```js
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
```

Replace:

- `$(selector)` with `document.querySelector` / `querySelectorAll`.
- `.click(fn)` with `addEventListener("click", fn)`.
- `.attr()` with `getAttribute` / `setAttribute`.
- `.data("href")` with `dataset.href`.
- `.show()` / `.hide()` with `hidden` or CSS classes.
- `.fadeOut().remove()` with CSS transition plus `remove()`, or immediate `remove()`.
- `$.ajax` with `fetch`.
- `serializeArray()` with `new FormData(form)` or explicit input collection.

Create a shared static helper for tooltips:

```js
function initPortalTooltips(root = document) {
  if (!window.bootstrap || !window.bootstrap.Tooltip) return;
  root.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((element) => {
    const existing = window.bootstrap.Tooltip.getInstance(element);
    if (existing) existing.dispose();
    window.bootstrap.Tooltip.getOrCreateInstance(element, { offset: [0, 2] });
  });
}
```

Use it instead of repeated `$(...).tooltip()` snippets.

### Phase 3: Replace jQuery UI

Global search is the most important jQuery UI dependency because it appears on every page.

Recommended replacement:

- Use `fetch("{% url 'api_players_clubs_and_tournaments_list' %}?typedText=...")`.
- Render a positioned `<ul role="listbox">`.
- Add keyboard support for up/down/enter/escape.
- Navigate to `item.href` on select.

For player registration date input:

- Prefer `input[type="date"]` if the UX is acceptable.
- Otherwise use a small non-jQuery picker loaded only on `register/player.html`.

After this, remove global jQuery UI CSS/JS.

### Phase 4: Replace Select2

`register/team.html` is the only Select2 page. Good replacements:

- Tom Select with remote loading.
- Slim Select if remote behavior is enough.
- A small custom async player combobox if the API shape is simple.

This does not need to block global jQuery removal if it is loaded page-locally, but it does block complete jQuery removal.

### Phase 5: Replace or Isolate DataTables

DataTables is used by six partials. There are two viable approaches:

1. Keep DataTables temporarily, but page-load it only where needed.
2. Replace it with server-side sorting/search/pagination and small native JS enhancements.

The second option fits this Django app better because several newer tables already use server-side pagination/custom markup. It also avoids shipping a client-side grid on every page.

Per-file notes:

- `clubs/clubs_table.html`: replace DataTables search/order/length menu with server query params.
- `seasons/players_list.html`: replace footer filters with server-side filter controls, or native table filtering if the data set is small.
- `player_future_tournaments.html`, `player_past_away_tournaments.html`, `player_past_tournaments.html`: likely simple enough for native sort or server-side ordering.
- `tournament_teams.html`: needs sorting plus admin save behavior; migrate admin save to `fetch` separately from table replacement.

### Phase 6: Remove jQuery

Remove from `common/head.html` only after these are done:

- No `$(...)`, `jQuery`, `$.ajax`, `$.map`, or `$.fn` in app-authored code.
- DataTables is removed or loaded with a non-jQuery version/alternative.
- jQuery UI is removed.
- Select2 is removed.
- Bootstrap jQuery-style calls are replaced with native Bootstrap API or custom behavior.

Verification command:

```sh
rg -n --glob '!RTK.md' --glob '!*.min.js' --glob '!*.min.css' '(jQuery|\\$\\(|\\$\\.|\\.DataTable\\(|\\.datepicker\\(|\\.autocomplete\\(|\\.select2\\(|jQuery\\.fn|\\.tooltip\\(|\\.tab\\()' components/web-api/application
```

## Bootstrap Removal Options

### Option A: Keep Bootstrap CSS and JS

Lowest risk. Only remove jQuery and page-load heavy plugins. This keeps current layout and interactive behavior.

### Option B: Keep Bootstrap CSS, Remove Bootstrap JS

Moderate risk. Replace:

- Tooltips with a custom tooltip helper.
- Tabs/pills with a custom tab controller.
- Dropdowns with a custom accessible menu controller.
- Collapse with a custom disclosure controller.
- Alert dismiss with a native click handler.

This saves about 24 KB gzip globally, but the custom accessibility surface is non-trivial.

### Option C: Remove Bootstrap CSS and JS

High risk and high effort. Required work:

- Replace layout grid classes (`container`, `row`, `col-*`) with portal layout classes.
- Replace spacing/flex/text/background utilities.
- Replace `btn`, `badge`, `card`, `table`, `alert`, `nav`, `dropdown`, `pagination`, `form-control`, `form-select`.
- Replace `crispy_bootstrap5` with custom Crispy templates or manual form rendering.
- Update Python-generated HTML in `templatetags/app_filters.py`.
- Decide whether Bootstrap Icons stays. It is separate from Bootstrap CSS/JS but currently used broadly.

This should be a standalone frontend redesign/design-system project, not part of jQuery removal.

## Practical Recommendation

Do not start by removing Bootstrap. Bootstrap CSS is not the main performance issue, and it is deeply tied to templates and forms.

Start by reducing global JavaScript:

1. Add asset blocks.
2. Move DataTables and FullCalendar out of the global head.
3. Replace global search autocomplete without jQuery UI.
4. Rewrite small jQuery snippets.
5. Replace DataTables and Select2.
6. Remove jQuery.

Expected result: most global jQuery-related weight disappears while preserving the Bootstrap-based UI. Bootstrap can then be addressed intentionally if the goal is design independence rather than bundle weight.
