# Tournament list frontend pilot

The tournament list is a Django page with a desktop table and one card layout for phones and tablets. Search, sort, filter, and pagination use GET requests; links and results are present in the first HTML response. The server sends 25 tournaments by default on desktop and 10 on phones, using the browser’s mobile hint or user agent. Open the number next to the page-size label to choose 5, 10, 25, 30, or 50. An explicit selection is preserved in search, filters, and pagination.

## Build and maintain

Use Node 22.22.0. From `components/web-api/frontend`, run:

```sh
npm ci
npm run build
```

CI and the web Docker image use the same commands. For browser verification, use the existing stack and database:

```sh
docker compose -p petanque-portal up -d --no-deps --build petanque_portal_web_api
```

Vite writes `application/static/vite/manifest.json` and its hashed assets. Django's `vite_stylesheet` tag reads the manifest from the image and joins the filename to `STATIC_URL`. The build imports only the Basecoat components used by the list and prefixes their classes to avoid collisions with Bootstrap. Tailwind compiles the component CSS without Preflight. There are no utility classes to discover in Django templates for this entry.

- To change the color or focus ring of primary buttons, edit `--list-primary` in [theme.css](../components/web-api/frontend/src/theme.css).
- Use the [shared badge template](../components/web-api/application/federation/templates/common/badge.html) for tags and status labels. Pass a label, a tone, and `shape="status"` for a rounded status badge. The list, tournament detail, and registration summary share the badge styles in [style-v2.css](../components/web-api/application/static/style-v2.css). Card sizing stays in [tournaments.css](../components/web-api/frontend/src/tournaments.css).
- To add a column for data already in a row, add a `<th scope="col">` and corresponding `<td>` in [tournaments_table.html](../components/web-api/application/federation/templates/tournaments/tournaments_table.html). For example, split the existing team count into its own column by moving the `team_count.html` include into the new cell. The card can continue to use the same include.
- Shared list controls are in [templates/common/list](../components/web-api/application/federation/templates/common/list). To reuse the pilot styles on another page, expose the entry in that page's head and move the theme and shared controls to a common wrapper as part of that migration.

The deploy script runs `collectstatic` before replacing the web container. It copies the Vite output under `vite/`; S3 manifest postprocessing skips that prefix so Vite keeps ownership of asset names. Deploys do not clear old files. To roll back, rebuild the prior revision and run its normal deploy sequence. Keep previously published Vite objects available while any cached HTML or prior revision can reference them. The pilot currently ships CSS only, with no linked fonts or JavaScript modules in the bundle. The local web service was switched back to the baseline revision and restored to the pilot using the existing Compose project and data. Local `collectstatic` copied the fingerprinted CSS byte for byte. Production S3 serving and cache lifecycle still need a release check.

## Comparison on November 17, 2026

Baseline: `8e49265`. Initial pilot measurement: `40ee3e7`. Control: `/tournaments/?period=past&per_page=5&page=2`. Same local data, Ukrainian, Chromium at 1440 × 900, three fresh browser contexts per revision, HTTP cache disabled through CDP. Count successfully transferred scripts and styles via `Network.loadingFinished.encodedDataLength`, including third-party resources. Browser transfer varies with CDN responses.

| Metric | Before | Pilot |
| --- | ---: | ---: |
| Site-authored CSS for the replaced list styles, before minification | 22,790 B | 7,533 B (−67%) |
| Median CSS transfer | 97,059 B | 95,398 B (−1.7%) |
| Median JS transfer | 312,584 B | 196,458 B (−37.2%) |
| Document requests at 390 px on `?period=past` | 2 | 1 |
| Result layouts | 3 | 2 |

The CSS source calculation counts the bytes removed from `style-v2.css` for list-specific table, filter, card, pagination and empty-state rules (including 162 removed rule blocks and two trimmed selector groups) and compares them with every authored CSS file in the pilot entry, including its theme and shared controls. Rules retained for legacy pages are excluded from both sides of this calculation. The compiled CSS includes the Basecoat component styles and Tailwind output.

Transfer bytes by run: CSS 96799, 97374, 97059 → 95398, 95463, 95137; JS 296097, 312584, 312905 → 196458, 196447, 196776. DataTables and FullCalendar are absent from the pilot but remain available on legacy routes. Bootstrap, jQuery, and jQuery UI still serve the shared navigation and search. Select2 is used on legacy form pages. Facebook SDK is counted separately from portal-owned JavaScript in the asset inventory below.

<details>
<summary>Successfully transferred CSS / JS inventory</summary>

| Asset | Baseline | Pilot |
| --- | --- | --- |
| `/static/bootstrap-theme.css` | css | css |
| `/static/portal-ui.js?v=de336fe17526` | js | — |
| `/static/style-v2.css?v=8d7e2d2601c6` | css | — |
| `https://cdnjs.cloudflare.com/ajax/libs/flag-icon-css/2.3.1/css/flag-icon.min.css` | css | css |
| `https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.13.2/themes/smoothness/jquery-ui.min.css` | css | css |
| `https://cdn.jsdelivr.net/npm/bootstrap-icons/font/bootstrap-icons.css` | css | css |
| `https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.13.2/jquery-ui.min.js` | js | js |
| `https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js` | js | js |
| `https://cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js` | js | js |
| `https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css` | css | — |
| `https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js` | js | — |
| `https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js` | js | — |
| `https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js` | js | — |
| `https://connect.facebook.net/uk_UA/sdk.js` | js | js |
| `https://connect.facebook.net/uk_UA/bundle/sdk.js/` | js | js |
| `/static/vite/assets/tournaments-DG1Npbsf.css` | — | css |
| `/static/portal-ui.js?v=291a8912208b` | — | js |
| `/static/style-v2.css?v=6200658d5247` | — | css |

</details>

## Review walkthrough

1. Open the control URL at 390, 820 and 1440 px. Compare the screenshots at the same viewport. At 390 px, look at the long «Кубок Кошового» title and Details link.
2. At 390 px, enter `Кубок` and click **Знайти** or press Enter. Follow **Next page**, reopen its address in a new tab, then disable JavaScript and repeat. The selected query, results and real pagination links are in the HTML. Check a no-match query and reset.
3. Compare the table above. Make the two example changes (badge, existing-field column) on a throwaway patch.

The baseline gallery also captures home, tournament detail (`/tournament/750`), player ratings, clubs, documents, registration, and an empty tournament search at 1440 px.

The browser smoke check covered 320, 390, 768, 820, 1024 and 1440 px; the English search control, legacy rating route, and shared global autocomplete also passed. Physical iOS and Android devices, Safari and Firefox, production S3, and Search Console were outside this local run.
