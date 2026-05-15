# Frontend And UI Audit

## Summary

The frontend is server-rendered Django templates with Bootstrap styling and jQuery-based enhancements. This is appropriate for the portal's current page-oriented behavior. A full React/Vite migration is not a top priority.

## Frontend Footprint

- Templates: 63 HTML templates under `federation/templates/`
- Template lines: about 3,975
- Static files: 77 files under `application/static/`
- Main custom stylesheet currently included: `style-v2.css`
- Older stylesheet present but apparently not included: `style.css`

## How Styling Works

Most pages extend `common/page_base.html`, which includes:

- `common/header.html`
- `common/head.html`
- `common/menu.html`
- `common/footer.html`
- `common/foot.html`

`common/head.html` loads:

- local `bootstrap-theme.css`
- local `style-v2.css`
- CDN Bootstrap Icons
- CDN Bootstrap JS
- CDN jQuery
- CDN jQuery UI
- CDN DataTables
- CDN FullCalendar

Styling is mostly Bootstrap classes in templates plus small custom overrides.

## How JavaScript Works

JavaScript is mostly inline in templates:

- global search autocomplete in `common/menu.html`
- GDPR cookie banner in `common/header.html`
- DataTables initialization in table templates
- FullCalendar initialization in `tournaments/calendar.html`
- Select2 initialization in `register/team.html`

`static/scripts.js` exists but does not appear to be included by templates.

## UI/Frontend Smells

- Inline JavaScript is scattered across many templates.
- DataTables setup is duplicated.
- Assets are mixed between CDN and local vendored copies.
- Old local copies of DataTables/FullCalendar/Moment exist while newer CDN versions are used.
- `style.css` appears unused but contains substantial old styling.
- Some Bootstrap 3-era classes/patterns remain while Bootstrap 5 is loaded.
- Dark-theme toggle code exists but is commented/disabled.

## Recommendation

Keep Django templates for now. Improve frontend incrementally:

1. Identify actually loaded CSS/JS.
2. Remove unused old static assets or clearly mark them as legacy.
3. Move repeated inline JS into organized static files.
4. Create small reusable initializers for DataTables, search, calendar, and Select2.
5. Avoid a full React/Vite migration unless specific pages become highly interactive.

