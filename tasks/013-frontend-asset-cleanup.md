# Task 013: Frontend Asset Cleanup

## Goal

Make frontend assets easier to understand and maintain without moving to a JavaScript framework.

## Scope

### 1. Audit Asset Loading

Determine which files are actually loaded vs dead:
- `style.css` — appears unused (only `style-v2.css` is included)
- `scripts.js` — exists but not included by any template
- Local DataTables JS/CSS — likely unused (CDN versions loaded)
- Local FullCalendar/Moment — likely unused (CDN versions loaded)
- `bootstrap-theme.css` — used

### 2. Remove Or Mark Dead Assets

- If confirmed unused: remove `style.css`, `scripts.js`, local DataTables files, local calendar files
- If uncertain: move to `static/legacy/` directory

### 3. Extract Repeated Inline JavaScript

Templates with significant inline JS:
- `common/menu.html` — global search autocomplete
- `common/header.html` — GDPR cookie banner
- Multiple templates — DataTables initialization
- `tournaments/calendar.html` — FullCalendar init
- `register/team.html` — Select2 init

Extract to organized static files:
```
static/js/
├── search.js         ← global search autocomplete
├── datatables-init.js ← reusable DataTables setup
├── calendar.js       ← FullCalendar initialization
├── gdpr.js          ← cookie consent
└── registration.js  ← Select2 and form logic
```

### 4. Clean Up CDN References

Document all external CDN dependencies in one place:
- jQuery 3.6.0
- jQuery UI
- Bootstrap 5.3.2
- Bootstrap Icons
- DataTables 1.13.6
- FullCalendar 6.1.15

Consider self-hosting if CDN availability is a concern for Ukrainian users.

## Acceptance Criteria

- Asset loading is documented
- Unused assets are removed or clearly marked legacy
- Inline JS reduced (DataTables init shared across pages)
- No frontend behavior regression on main pages
- Page load doesn't break if CDN is slow (critical JS should be local)

## Complexity

M

## Risk

Low — can be done page by page.

## Big Win

Medium — reduces confusion and makes templates cleaner.
