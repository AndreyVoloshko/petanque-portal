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

Tournaments, player ratings, season ratings, and the club directory use the same filter form. The form uses Bootstrap inputs, selects, buttons, and grid utilities. Each view supplies its labels, choices, and preserved URL parameters. The remaining filter CSS covers icons, focus, and the tournament search button's keyboard reveal on desktop. The tournament bundle no longer builds Basecoat text input and select styles.

The ratings lists use the shared athlete card at both phone and tablet widths. Bootstrap's grid puts cards in one column below 768 px and two columns at wider card widths. The former ratings-specific card layout stylesheet was removed.

Compared with `b17efd9`, authored CSS across `style-v2.css` and the CSS sources in `frontend/src` fell from 13,505 to 13,148 lines. That is 357 fewer lines and 8,431 fewer uncompressed bytes. The source count excludes generated and vendor CSS.

Chromium verified that tournament, rating, and club filters submit and preserve URL state with JavaScript disabled. Layout checks covered 320–1440 px and verified the tournament search button's keyboard reveal.
