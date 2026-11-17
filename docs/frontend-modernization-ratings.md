# Frontend pilot step 2 — player and season ratings

Django already rendered the ratings table, cards and ranking positions. This step keeps that rendering, shares the filter form between current and historical ratings, and uses the tournament list's pagination and page-size controls. The controls submit GET requests and work with JavaScript disabled. DataTables and FullCalendar are omitted from these pages. The shared navigation, autocomplete and tooltips still load their existing assets.

The server sends 25 athletes on detected phones and 50 on other devices. An explicit size of 25, 30, 50 or 100 wins and stays in filter, pagination and season-year links. The previous desktop-window and tablet breakpoint that substituted 30 rows was based on JavaScript viewport detection. Resizing a desktop window still changes the layout via CSS. Row count uses the device hint or user agent on the request. On mobile the filter panel scrolls with the page so the results anchor clears the header. The Search button applies the selected filters together, and Enter still submits the search field.

## Measurements

Baseline `43f2abc`. The asset control was `/players/licence/?per_page=25` with the existing local data, Ukrainian locale and 900 px viewport height. At each width, take the median of three Chromium loads in fresh contexts with HTTP cache disabled. Count successful stylesheet and script transfers via CDP `Network.loadingFinished.encodedDataLength`, including CDN files. Response sizes vary slightly across runs. For the mobile document count, open `/players/licence/` without a size override; count top-level requests.

| Metric | Before | Step 2 | Change |
| --- | ---: | ---: | ---: |
| CSS transferred at 1440 px | 94,087 B | 93,262 B | −0.9% |
| JS transferred at 1440 px | 312,139 B | 196,617 B | −37.0% |
| CSS transferred at 390 px | 93,694 B | 93,178 B | −0.6% |
| JS transferred at 390 px | 312,515 B | 200,422 B | −35.9% |
| Mobile document requests | 2 | 1 | −1 |
| Horizontal overflow at 390 px | 20 px | 0 px | −20 px |
| Authored CSS source | 13,397 lines / 269,342 B | 13,474 lines / 271,592 B | +77 lines |
| Related templates | 445 lines | 348 lines | −97 lines |
| Shared portal JS source | 513 lines | 484 lines | −29 lines |

The runs transferred the following bytes in navigation order.
- 1440 px. CSS 94027, 94419, 94087 → 92935, 93262, 93701. JS 312489, 312139, 312121 → 196617, 196303, 200118.
- 390 px. CSS 93759, 93664, 93694 → 92985, 93320, 93178. JS 312496, 312515, 312824 → 196651, 200422, 200495.

The code counts compare the same files at the baseline and after the change. Authored CSS includes `style-v2.css` and every CSS source in `frontend/src`, with shared files counted once. Template counts cover the current and season page templates, shared rating filter form, table and page-size partial. The JavaScript count covers `portal-ui.js`. The ratings entry reuses styles still required by other pages, so the authored CSS grows even as the page transfers fewer assets.

## Typography reference

Use this as the before-and-after reference for the Ukrainian ratings page at 1440 and 390 px. The declared family starts with **Source Sans Pro**, followed by the existing system and sans-serif fallbacks. Each cell lists font size, weight, text color and line height. Keep the measured weight even when the closest rendered weight depends on the available font.

| Element | Desktop at 1440 px | Phone at 390 px |
| --- | --- | --- |
| Page title | 37.6 px · 800 · `#172033` · 41.36 px | 29.6 px · 800 · `#172033` · 32.56 px |
| Subtitle | 15.68 px · 650 · `#66748a` · 21.95 px | 14.4 px · 650 · `#66748a` · 20.16 px |
| Search input | 14.4 px · 650 · `#23304a` · 21.6 px | 14.4 px · 650 · `#23304a` · 21.6 px |
| Filter selects | 14.4 px · 700 · `#23304a` · 21.6 px | 14.4 px · 700 · `#23304a` · 21.6 px |
| Table heading | 13.12 px · 800 · `#23304a` · normal | |
| Rank in the table | 12.8 px · 800 · `#ffffff` · 12.8 px | |
| Athlete name | 14.4 px · 750 · `#0d3b66` · 17.28 px | 16.32 px · 800 · `#23304a` · 18.28 px |
| Points | 12.8 px · 800 · `#3158d4` · 12.8 px | 16 px · 800 · `#08264a` · 17.6 px |
| Metric label in a card | | 12.16 px · 600 · `#5f7285` · 13.98 px |
| Pagination summary | 13.76 px · 650 · `#66748a` · 20.64 px | 13.76 px · 650 · `#66748a` · 20.64 px |
| Disabled pagination arrows | 13.76 px · 800 · `#b1bbc9` · 13.76 px | 13.12 px · 800 · `#b1bbc9` · 13.12 px |

The table heading uses a `#fbfdff` background and 14.4 × 16 px padding. The selects use the same background on their wrappers, with 32 px of trailing space inside the select for the arrow. Select focus uses a soft blue-gray shadow and a slightly darker border. Page controls use white, `#dbe5ef` borders, and `#1f5f8b` for the current page. Page size now uses a disclosure styled like the pager.

## Lessons for the next migration

1. Before changing a page, capture screenshots and computed styles at desktop and phone widths, using the same route, filters, language and data. Wait for fonts to load. Record font family, size, weight, line height, text color, background, padding, alignment and icon size for page headings, table headers, dates, tags, status badges, links, actions and form controls.
2. Reuse the existing typography and colors when replacing markup or controls. Check the rendered styles after the CSS build. A component class can change inherited type, weight, padding or color even when the template uses the same text.
3. Compare a date and weekday together, the alignment of help icons with their labels, a long name, card metadata, both active and disabled pagination, and a keyboard-focused select. Test narrow widths for horizontal overflow and check cards that have missing optional fields. Record intentional changes alongside the comparison.
4. Measure authored source lines and browser transfers separately. Count reused styles once in the source total, and count all requested assets in the browser totals. Check that search, filters and pagination still work without JavaScript.

## Verification

- The Docker image built both Vite entries. All 262 Django tests passed.
- Chromium at 320, 390, 820 and 1440 px showed no horizontal overflow. Search by Enter, applying filters, changing the page size, following the next-page link and loading empty results passed with JavaScript disabled. The page number, filters and explicit size stayed in the URL.
- The same 25 athlete names, ranks and points appeared before and after on the licensed ratings control, on page 2 of the licensed women's filter, and on the 2024 season page.
- Chromium verified the select focus indicator by pointer and Tab on the tournament and ratings lists. It also verified that DataTables is absent from current and seasonal ratings and still loads on the club listing. Safari and physical mobile devices were outside this run.
