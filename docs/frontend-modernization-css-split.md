# CSS split for the frontend pilot

The tournaments, player ratings, and season ratings pages use route stylesheets and shared Vite assets. The header, footer, page layout, and CSS tokens live in separate source files that compile into one shell asset. The shared list asset contains the table and pagination styles. The shared filter bar owns the select focus styles. Both lists extend the same Django table template and supply their own headers and rows.

The athlete card is one Django template and one independently cached stylesheet. The home page, club details, title registries, and mobile ratings use it. Ratings place the cards beside the desktop table in the template and switch between them with CSS. The home page still uses the reduced legacy stylesheet for its other content.

## CSS downloaded

Baseline commit `8629f95`. The table uses the median of three Chromium loads per route and width. Each load used a fresh browser context with the HTTP cache disabled, the same seeded local data, Ukrainian locale, and a 900 px viewport height. The totals count successfully transferred stylesheet bytes from CDP `Network.loadingFinished.encodedDataLength`, including Bootstrap, icons, and other third-party CSS.

| Route | Width | Before | After | Change |
| --- | ---: | ---: | ---: | ---: |
| `/tournaments/?period=past&per_page=5` | 390 px | 97,257 B | 64,085 B | −34.1% |
| `/tournaments/?period=past&per_page=5` | 1440 px | 96,632 B | 64,115 B | −33.7% |
| `/players/licence/?per_page=25` | 390 px | 93,077 B | 64,449 B | −30.8% |
| `/players/licence/?per_page=25` | 1440 px | 93,011 B | 64,815 B | −30.3% |
| `/seasons/2024?per_page=25` | 390 px | 93,094 B | 64,345 B | −30.9% |
| `/seasons/2024?per_page=25` | 1440 px | 93,273 B | 64,777 B | −30.6% |
| `/` | 390 px | 93,737 B | 94,225 B | +0.5% |
| `/` | 1440 px | 94,061 B | 94,274 B | +0.2% |

The three loads transferred the following byte counts.

- `/tournaments/?period=past&per_page=5` at 390 px, 96635, 97257, 97275 → 64085, 64613, 64039. At 1440 px, 96524, 96632, 96933 → 64115, 64663, 63981.
- `/players/licence/?per_page=25` at 390 px, 93613, 93077, 92929 → 64449, 64416, 65083. At 1440 px, 93011, 93005, 93334 → 64473, 64815, 65000.
- `/seasons/2024?per_page=25` at 390 px, 93094, 93042, 93349 → 64625, 64345, 64243. At 1440 px, 93257, 93315, 93273 → 65002, 64777, 64719.
- `/` at 390 px, 93699, 93737, 94060 → 94225, 94822, 93845. At 1440 px, 94108, 93681, 94061 → 93959, 94858, 94274.

| Authored CSS scope | Before | After | Change |
| --- | ---: | ---: | ---: |
| `style-v2.css` | 12,822 lines / 253,317 B | 10,475 lines / 206,171 B | −2,347 lines / −47,146 B |
| `style-v2.css` plus all authored CSS in `frontend/src` | 13,489 lines / 271,528 B | 13,505 lines / 272,064 B | +16 lines / +536 B |

Desktop and phone CSS Coverage on the baseline helped locate styles the pilot and home page shared. Extraction moved those rules to their respective components. The combined source totals count each component file once. Measured cold CSS transfer on the home page was up by less than 1%. Its athlete card now shares the same cacheable URL as ratings.

## Verification

- The existing Docker image built all stylesheet entries. All 263 Django tests passed. A regression test checks that the three list routes load the shared shell and list assets and that the home page loads the athlete-card asset.
- Chromium checks covered layout at 320, 390, 820, and 1440 px, including matching table and pagination styles and filter preservation during paging and page-size changes with JavaScript disabled.
- Browser checks also covered the cookie banner, mobile navigation, autocomplete, athlete links, title registries, club pages, tournament sort, and the empty state.
- Shared template and style owners are [the athlete card](../components/web-api/application/federation/templates/common/athlete_card.html), [the card stylesheet](../components/web-api/frontend/src/athlete-card.css), [the table template](../components/web-api/application/federation/templates/common/list/table.html), [the table stylesheet](../components/web-api/frontend/src/list-table.css), and [the shell tokens](../components/web-api/frontend/src/tokens.css).

## Optional scripts

The home page skips DataTables. Home, tournaments, and both ratings lists skip the Facebook SDK, which they had loaded without an embed. FullCalendar loads with the calendar template, where it renders the calendar and fetches events.

The medians below use three Chromium loads per width with caching disabled. They compare `93baf58` with this follow-up. The tournament URL was `/tournaments/?period=past&per_page=5`.

| Page | CSS transferred | JavaScript transferred | JavaScript change |
| --- | ---: | ---: | ---: |
| Home at 390 px | 94,538 B → 92,210 B | 312,277 B → 114,817 B | −63.2% |
| Home at 1440 px | 94,396 B → 92,258 B | 312,407 B → 114,828 B | −63.2% |
| Tournaments at 1440 px | 64,648 B → 64,594 B | 200,173 B → 114,819 B | −42.6% |


## Shared filters and one athlete card layout

Tournaments, player ratings, season ratings, and the club directory use the same filter form. The form uses Bootstrap inputs, selects, buttons, and grid utilities. Each view supplies its labels, choices, and preserved URL parameters. Tournament and rating searches submit with Enter on desktop, where the button appears on keyboard focus. On phones and tablets, the submit button sits beside the search field. The remaining filter CSS covers icons, focus, and layout. The tournament bundle no longer builds Basecoat text input and select styles.

The ratings lists use the shared athlete card at both phone and tablet widths. Bootstrap's grid puts cards in one column below 768 px and two columns at wider card widths. The former ratings-specific card layout stylesheet was removed.

Compared with `b17efd9`, authored CSS across `style-v2.css` and the CSS sources in `frontend/src` fell from 13,505 to 13,148 lines. That is 357 fewer lines and 8,431 fewer uncompressed bytes. The source count excludes generated and vendor CSS.

Chromium verified that tournament, rating, and club filters submit and preserve URL state with JavaScript disabled. Layout checks covered 320–1440 px and verified the tournament search button's keyboard reveal.

## Shared stylesheet measurements before the palette cleanup

The comparison at `db95e43` used the same routes, data, widths, and three-run method as the CSS split baseline at `8629f95`.

| Page | Width | Before | Final | Change |
| --- | ---: | ---: | ---: | ---: |
| Tournaments | 390 px | 97,257 B | 63,968 B | −34.2% |
| Tournaments | 1440 px | 96,632 B | 63,948 B | −33.8% |
| Player ratings | 390 px | 93,077 B | 64,472 B | −30.7% |
| Player ratings | 1440 px | 93,011 B | 64,235 B | −30.9% |
| Season ratings | 390 px | 93,094 B | 64,049 B | −31.2% |
| Season ratings | 1440 px | 93,273 B | 64,260 B | −31.1% |
| Home | 390 px | 93,737 B | 91,913 B | −1.9% |
| Home | 1440 px | 94,061 B | 91,521 B | −2.7% |

At this checkpoint, the measured authored sources went from 14,065 lines and 276,618 bytes at `8e49265` to 13,148 lines and 263,633 bytes. That is 917 lines and 12,985 uncompressed bytes removed, counting the legacy file and every authored frontend CSS file once. All 264 Django tests passed at this checkpoint.

## Palette and spacing

- Use the `--list-*` palette in [tokens.css](../components/web-api/frontend/src/tokens.css). Use `--list-text` for headings, `--list-ink` for body text, and `--list-muted` for metadata, secondary labels, and icons. Use the shared surface and border tokens for tables, filters, cards, and pagination.
- Use the primary blue for interactive controls and the page accent for links and selected pagination. Use the semantic palette for tags, metrics, and awards. The rating and tournament badge variants use their named background, border, and text tokens from the visual references. Other badge variants use the default tint, and neutral tournament statuses share the muted tone.
- Use `--space-1`, `--space-2`, `--space-3`, `--space-4`, `--space-6`, and `--space-8` for padding and gaps. At a 16 px root size these are 4, 8, 12, 16, 24, and 32 px. Let content and padding size cards and labels. Keep explicit sizes for avatars and interactive targets where the size serves a purpose.
- Use Bootstrap for buttons and layout utilities. Vite compiles the shared styles and route CSS directly. The Basecoat and Tailwind build dependencies have been removed.

The follow-up consolidated overlapping tournament breakpoints, desktop and mobile badge styles, and repeated athlete-card and rating rules. The Vite component styles used 163 distinct hex or RGB values outside the token file before this pass. They now take their colors from the shared palette. The legacy palette in the same token file still serves pages that load `style-v2.css`.

| Measure | Before cleanup (`7379ca9`) | After cleanup | Change |
| --- | ---: | ---: | ---: |
| Authored CSS in `frontend/src` | 2,692 lines | 2,233 lines | −459 lines (17.1%) |
| Authored CSS including `style-v2.css` | 13,148 lines / 263,633 B | 12,689 lines / 256,102 B | −459 lines / −7,531 B |
| Compiled tournament entry | 16,299 B | 8,320 B | −49.0% |
| Compiled tournament entry, gzip | 3,699 B | 1,989 B | −46.2% |
| All compiled Vite CSS entries, gzip | 13,783 B | 11,236 B | −18.5% |

The full pilot went from 14,065 to 12,689 authored CSS lines, a reduction of 1,376 lines (9.8%) and 20,516 bytes (7.4%). The compiled measurements sum each standalone stylesheet from the Vite manifest once, with gzip measured per file. Bootstrap, third-party CSS, and legacy CSS are outside the compiled Vite totals.

### CSS transferred after the cleanup

The same local URLs and three-run Chromium method were used for the new measurements. CDN and response sizes vary across runs. The baseline comparison is against `8629f95`.

| Page | Width | Baseline | Before cleanup | After cleanup | Baseline change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tournaments | 390 px | 97,257 B | 63,968 B | 62,560 B | −35.7% |
| Tournaments | 1440 px | 96,632 B | 63,948 B | 61,989 B | −35.9% |
| Player ratings | 390 px | 93,077 B | 64,472 B | 63,725 B | −31.5% |
| Player ratings | 1440 px | 93,011 B | 64,235 B | 63,738 B | −31.5% |
| Season ratings | 390 px | 93,094 B | 64,049 B | 63,696 B | −31.6% |
| Season ratings | 1440 px | 93,273 B | 64,260 B | 63,681 B | −31.7% |
| Home | 390 px | 93,737 B | 91,913 B | 91,237 B | −2.7% |
| Home | 1440 px | 94,061 B | 91,521 B | 91,598 B | −2.6% |

Chromium verified filtering with JavaScript disabled, date sort at card and table widths, tournament switches, empty state, keyboard focus, and card layout from 320 to 1440 px. The Docker asset build and all 264 Django tests passed.

## Club directory and tournament registrations

The club directory and tournament detail now load route-specific CSS. They share the table shell and pagination with tournaments and ratings. Django sorts and paginates singles and team registrations, so those controls work without JavaScript. The last public DataTables asset include was removed, and both routes skip the Facebook SDK.

The club directory reuses the filter bar, points and average badge tokens, and shared spacing. It uses one card per row on phones and two on tablets. Founding dates use standalone Ukrainian month names. The founding-year selector was removed, and existing URLs with a year parameter still work. Tournament registration reuses the extracted detail stylesheet for the shared header.

| Authored CSS scope | Before (`9055782`) | After | Change |
| --- | ---: | ---: | ---: |
| `style-v2.css` | 10,461 lines / 205,847 B | 7,079 lines / 133,605 B | −3,382 lines / −72,242 B |
| `style-v2.css` and authored frontend CSS | 12,802 lines / 259,336 B | 12,232 lines / 244,047 B | −570 lines / −15,289 B |

Cold transfer was measured against `9055782` with the existing local data and Ukrainian locale. Each cell is the median of three Chromium loads per viewport with the HTTP cache disabled. CDP `Network.loadingFinished.encodedDataLength` counts successful stylesheet and script responses, including shared and third-party assets. Routes were `/clubs/?per_page=25`, `/tournament/750` for singles, and `/tournament/809` for teams.

| Page | Width | CSS transferred | JavaScript transferred |
| --- | ---: | ---: | ---: |
| Club directory | 390 px | 94,408 B → 67,157 B (−28.9%) | 197,618 B → 110,562 B (−44.1%) |
| Tournament singles | 390 px | 98,368 B → 72,787 B (−26.0%) | 227,832 B → 110,534 B (−51.5%) |
| Tournament teams | 390 px | 98,284 B → 72,860 B (−25.9%) | 227,926 B → 110,547 B (−51.5%) |
| Club directory | 820 px | 94,613 B → 67,155 B (−29.0%) | 197,332 B → 110,481 B (−44.0%) |
| Tournament singles | 820 px | 98,230 B → 72,637 B (−26.1%) | 227,948 B → 110,837 B (−51.4%) |
| Tournament teams | 820 px | 98,151 B → 72,828 B (−25.8%) | 227,866 B → 110,579 B (−51.5%) |
| Club directory | 1200 px | 94,559 B → 67,192 B (−28.9%) | 197,325 B → 110,534 B (−44.0%) |
| Tournament singles | 1200 px | 98,303 B → 72,905 B (−25.8%) | 227,880 B → 110,534 B (−51.5%) |
| Tournament teams | 1200 px | 98,545 B → 72,779 B (−26.1%) | 227,595 B → 110,540 B (−51.4%) |
| Club directory | 1440 px | 94,639 B → 67,165 B (−29.0%) | 197,317 B → 110,515 B (−44.0%) |
| Tournament singles | 1440 px | 98,413 B → 72,846 B (−26.0%) | 227,640 B → 110,517 B (−51.5%) |
| Tournament teams | 1440 px | 98,618 B → 72,768 B (−26.2%) | 227,577 B → 110,538 B (−51.4%) |

Chromium checked layout from 320 to 1440 px and verified club filter submission, tournament sorting, page links, and page-size changes with JavaScript disabled. The container asset build and all 268 Django tests passed.

## Tournament detail refinement

The detail layout now reuses the shell's `portal-panel` surface atom for its header, summary metrics, information panels, people section, participants section, and mobile team cards. The repeated metric and label/value markup has one template each. Existing color tokens replace the local detail palette and all literal colors in the shared tournament badges. The five `--text-*` tokens define the component font-size scale, and the detail layout uses the shared spacing scale.

Unused hero facts, tab styling, obsolete table display resets, duplicate rules, and the DataTables-era `!important` declarations were removed. Color-coded organizer and arbiter tiles were replaced with compact neutral cards. Only the assigned main organizer and head arbiters appear initially. Native `details` exposes the remaining people, with the number of additional people in its summary. Repeated arbiter memberships are shown once, giving the head-arbiter role priority. Missing person records are skipped. The category suffixes are `I`, `II`, `НК` (`NC` in English), `CEP`, and `FIPJP` where applicable.

The incremental baseline below is `16db20b`. Both asset builds used the same Vite configuration, package lock, Node version, and separate gzip compression per file.

| Measure | Before refinement | After refinement | Change |
| --- | ---: | ---: | ---: |
| Tournament detail source | 2,107 lines / 43,668 B | 1,759 lines / 38,616 B | −348 lines / −5,052 B |
| All authored CSS, including `style-v2.css` | 12,232 lines / 244,047 B | 11,890 lines / 239,560 B | −342 lines / −4,487 B |
| Literal hex/RGB color references in detail and shared tournament badges | 123 | 0 | −123 |
| Compiled tournament detail CSS | 36,197 B | 32,765 B | −9.5% |
| Compiled tournament detail CSS, gzip | 6,177 B | 5,204 B | −15.8% |

The shared shell gzip grew from 3,825 to 3,948 B to supply the reusable panel atom, font-size tokens, and award palette. Shared tournament badges fell from 1,258 to 1,120 B gzip. Clubs changed from 1,902 to 1,893 B gzip. The combined shell, badges, and tournament detail entries fell from 11,260 to 10,272 B gzip.

Across the whole club/team migration, the comparison against `9055782` is now 12,802 → 11,890 authored CSS lines, a reduction of 912 lines and 19,776 uncompressed bytes. `style-v2.css` remains at 7,079 lines.

### Updated cold-load measurements

These replace the migration checkpoint's final values for the current PR. The baseline is still `9055782`, using the same three routes and medians of three Chromium loads per viewport with caching disabled.

| Page | Width | CSS transferred | JavaScript transferred |
| --- | ---: | ---: | ---: |
| Club directory | 390 px | 94,408 B → 67,376 B (−28.6%) | 197,618 B → 111,061 B (−43.8%) |
| Tournament singles | 390 px | 98,368 B → 72,074 B (−26.7%) | 227,832 B → 111,074 B (−51.2%) |
| Tournament teams | 390 px | 98,284 B → 72,028 B (−26.7%) | 227,926 B → 111,093 B (−51.3%) |
| Club directory | 820 px | 94,613 B → 67,442 B (−28.7%) | 197,332 B → 111,107 B (−43.7%) |
| Tournament singles | 820 px | 98,230 B → 71,840 B (−26.9%) | 227,948 B → 111,403 B (−51.1%) |
| Tournament teams | 820 px | 98,151 B → 72,177 B (−26.5%) | 227,866 B → 111,088 B (−51.2%) |
| Club directory | 1200 px | 94,559 B → 67,415 B (−28.7%) | 197,325 B → 111,092 B (−43.7%) |
| Tournament singles | 1200 px | 98,303 B → 72,177 B (−26.6%) | 227,880 B → 111,090 B (−51.3%) |
| Tournament teams | 1200 px | 98,545 B → 72,197 B (−26.7%) | 227,595 B → 111,024 B (−51.2%) |
| Club directory | 1440 px | 94,639 B → 67,373 B (−28.8%) | 197,317 B → 111,081 B (−43.7%) |
| Tournament singles | 1440 px | 98,413 B → 72,169 B (−26.7%) | 227,640 B → 111,083 B (−51.2%) |
| Tournament teams | 1440 px | 98,618 B → 72,074 B (−26.9%) | 227,577 B → 111,081 B (−51.2%) |

The existing Docker service was rebuilt and all 270 Django tests passed. Browser verification covered club filters, table/card breakpoints, sorting, and pagination, plus collapsed and expanded people sections at 320, 390, 768, 820, 1200, and 1440 px. The people disclosure was exercised with JavaScript disabled, including keyboard activation. Local tournaments with a national head arbiter, a category-II head arbiter, and 13 other arbiters were checked.

## Athlete and club profiles

Both profiles load route stylesheets in place of the site-wide legacy sheet. The club page retains the shared athlete cards, and both profiles use the existing panel and palette. Athlete history uses the shared table and pagination. Django renders the requested sort order and page so the URL can be shared and navigation works without JavaScript.

Tournaments, athlete ratings, season ratings, the club directory, and athlete history update in place on same-route filter, sort, or pagination actions. The browser preserves the current scroll position and restores it for Back and Forward. Regular GET links and forms handle navigation when JavaScript is disabled. Club roster filters continue to filter the cards already on the page.

| Authored CSS | Before (`77f546d`) | After | Change |
| --- | ---: | ---: | ---: |
| `style-v2.css` | 7,079 lines | 4,685 lines | −2,394 lines |
| All authored CSS including the legacy sheet | 11,890 lines / 239,560 B | 11,587 lines / 236,854 B | −303 lines / −2,706 B |

These figures exclude compiled and vendor CSS. Transfer totals are medians of three Chromium loads with the cache disabled, measured on the same local database and viewports. They include successfully transferred first-party and third-party stylesheets.

| Route | Width | Before | After | Change |
| --- | ---: | ---: | ---: | ---: |
| `/club/24` | 390 px | 84,364 B | 65,982 B | −21.8% |
| `/player/391` | 390 px | 84,028 B | 67,612 B | −19.5% |
| `/club/24` | 1440 px | 84,373 B | 65,984 B | −21.8% |
| `/player/391` | 1440 px | 84,235 B | 67,685 B | −19.6% |

## Home page

The home page uses a route-specific Vite stylesheet, the existing shell and tokens, and the shared buttons, panels, tournament badges and athlete cards. Cookie-banner breakpoints live with the shared header. The tournament carousels use CSS scroll snap and native JavaScript. The page uses the shared tooltip initializer. At the home migration checkpoint the header still loaded jQuery and jQuery UI.

| Authored CSS | Before (`5828cfe`) | After | Change |
| --- | ---: | ---: | ---: |
| `style-v2.css` | 4,685 lines / 91,569 B | 3,634 lines / 71,675 B | −1,051 lines / −19,894 B |
| All authored CSS including the legacy sheet | 11,582 lines / 236,705 B | 11,502 lines / 235,302 B | −80 lines / −1,403 B |

The authored totals exclude built and vendor CSS. Transfer totals are medians of three Chromium loads per width at `localhost:60102` with caching disabled and include all successfully transferred first-party and third-party stylesheets.

| Home viewport | Before | After | Change |
| --- | ---: | ---: | ---: |
| 390 px | 78,237 B | 66,103 B | −15.5% |
| 1440 px | 78,189 B | 65,864 B | −15.8% |

## Header navigation and search

The header keeps the portal's dark color and uses Bootstrap dropdowns and collapse for navigation. The desktop search stays visible in the header. On mobile its button opens a full-width panel with focus in the search field. Results from the existing API are capped at four per category in the header. Full names match in either order, clubs can match abbreviations, and requests from earlier input are canceled. The competitions menu links to upcoming and past lists, the same lists filtered to foreign events, and the calendar. The rated-only switch stays on the tournament list.

The header source added 170 authored CSS lines compared with `6b4aa83`. The browser no longer downloads jQuery UI CSS or JavaScript. jQuery remains for the shared `portal-ui.js` and pages that still depend on it.

| Home viewport | CSS before | CSS after | JS before | JS after |
| --- | ---: | ---: | ---: | ---: |
| 390 px | 66,408 B | 59,364 B | 112,543 B | 56,943 B |
| 1440 px | 65,984 B | 60,014 B | 111,765 B | 57,656 B |

Each column is the median of three local Chromium loads with cache disabled. Transfer includes successful first- and third-party stylesheet and script requests. The baseline is the running home migration build before the header change.

## Home competition empty states

The calendar is the primary home competition action and the full list uses a secondary button in the same teal palette. With no upcoming competitions, one full-width panel links to the archive. When only one category is empty, its panel links to the corresponding past list. The home stylesheet grew by 62 lines for the layout, responsive states, and button styles.

## Hero and header polish

The home hero now has registration and club links next to the federation intro, with the existing pétanque artwork in its own area. Header menus use a dark surface. On mobile, the account links are visible as soon as the navigation opens. The calendar action keeps its contrast when focused, including the pointer-focus state. Compared with `d7bec0a`, the home stylesheet lost 144 lines and the header stylesheet added 5 lines.

## Home action styling

Registration and Calendar use a muted blue fill with dark text. Find a club and All competitions use white with a soft border. All four actions are at least 48 px tall. The archive is a text link with a 44 px target. On phones and narrow tablets, the illustration is shorter and the archive link sits below the empty-state message. This refinement added 10 lines to the home stylesheet.

## Final PR #43 CSS review and measurements

The CSS review kept the tournament list's empty-state and focus rules in its own entry, replaced the home card's bespoke registration styling with Bootstrap button variables, and removed an unused tooltip exception and icon. Home and header reuse the palette, font-size scale, spacing scale, and one header-height token. Visual sizes for artwork and the carousel remain local. The review removed 114 authored CSS lines and 1,769 source bytes relative to `860fddc`.

The complete PR compares against `c1e388f`, the merge base with `master`. The source inventory counts `style-v2.css` and all authored `.css` files in `frontend/src`. It excludes generated bundles, SCSS, and vendored CSS.

| Authored CSS scope | Base | Final | Change |
| --- | ---: | ---: | ---: |
| `style-v2.css` | 4,685 lines / 91,569 B | 3,634 lines / 71,675 B | −1,051 lines / −19,894 B |
| All authored CSS | 11,587 lines / 236,854 B | 11,500 lines / 237,542 B | −87 lines / +688 B |

Both revisions ran on the existing local Docker service against the same database. The transfer checkpoint is `23cd584`. Each transfer figure is the median of three Chromium loads with the cache disabled, including first- and third-party stylesheets and scripts. Combined savings use the sum of the CSS and JavaScript medians. Images, fonts, HTML, and API requests are measured separately from this table.

| Route | Width | CSS base → final | JS base → final | Combined reduction |
| --- | ---: | ---: | ---: | ---: |
| Home | 390 px | 77,758 → 59,140 B | 110,222 → 56,970 B | 71,870 B (38.2%) |
| Home | 1440 px | 77,821 → 59,392 B | 110,213 → 57,746 B | 70,896 B (37.7%) |
| Past tournaments | 390 px | 64,660 → 58,453 B | 112,572 → 57,889 B | 60,890 B (34.4%) |
| Past tournaments | 1440 px | 64,682 → 58,759 B | 112,560 → 58,555 B | 59,928 B (33.8%) |
| Athlete ratings | 390 px | 66,162 → 59,869 B | 112,556 → 57,868 B | 60,981 B (34.1%) |
| Athlete ratings | 1440 px | 66,158 → 60,141 B | 112,539 → 58,539 B | 60,017 B (33.6%) |

### Search

The suggestion debounce measured 300 ms in the old jQuery UI widget. The new header uses 160 ms, serves repeated queries from its in-page cache, and cancels superseded requests. The widget shows up to four matches per category. Full names match in either order, exact name matches rank higher, and club abbreviations are searchable.

The same local API and database produced these uncompressed JSON sizes. The final header requests four results per category. The public endpoint still accepts requests without that parameter, and the new category field adds a small cost for queries that already had few matches.

| Query | Results base → final | JSON base → final | Change |
| --- | ---: | ---: | ---: |
| `Андрій` | 47 → 4 | 6,249 → 614 B | −90.2% |
| `Кубок` | 43 → 4 | 8,469 → 1,173 B | −86.1% |
| `Fair` | 3 → 3 | 609 → 669 B | +9.9% |

The final hero uses inline club and registration links in an invitation to try pétanque, with a separate federation news link to `https://petanque.org.ua/`. The mobile and desktop header applies a muted accent to open controls and uses white dropdown panels and search suggestions.

## Directories and footer

The five registry routes share a route-specific Vite stylesheet, the existing athlete-card template and its responsive grid. The card component owns title and role styling. Directory tabs use Bootstrap's native JavaScript. The registry routes skip jQuery and the shared jQuery-based portal script. The shared footer links to federation news and feedback using smaller, muted typography.

Each directory uses its own palette for active tabs and role panels. Card headers use lighter gradients in those same colors, with the original gradient on Structure. The compact dropdown uses the same palette. Sports Titles uses a pale gold selection and a gold medal. Gender and age icons on directory cards use the earlier gold `#d9a000`. Grid rows align the role text and athlete metadata across adjacent cards. A native select replaces the horizontal tab strip on phones and tablets. Phones have a back-to-top link beneath the cards.

The baseline is the PR #43 merge at `045701d`, whose file tree matches `af0e55f`.

| Measure | Base | Directories and footer | Change |
| --- | ---: | ---: | ---: |
| `style-v2.css` | 3,634 lines / 71,675 B | 3,042 lines / 59,686 B | −592 lines / −11,989 B |
| All authored CSS | 11,500 lines / 237,542 B | 11,231 lines / 234,061 B | −269 lines / −3,481 B |
| Authored CSS and Stylish Portfolio SCSS | 11,789 lines / 243,402 B | 11,500 lines / 239,491 B | −289 lines / −3,911 B |
| First-party CSS on each registry route, raw | 338,022 B | 273,508 B | −64,514 B (−19.1%) |
| First-party CSS on each registry route, gzip | 52,142 B | 41,796 B | −10,346 B (−19.8%) |

Per-route sizes sum the local Vite assets and the legacy stylesheet where present. The gzip figures compress each file independently. Browser network transfer depends on the server and cache.

The directory navigation script is 564 B raw and 305 B gzip. The former jQuery and portal UI requests transferred 31,175 B combined on a Chromium load of Structure with caching disabled. The updated directories were checked in Chromium on the existing Compose service with the local database.
