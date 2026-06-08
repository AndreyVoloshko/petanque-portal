# Seasons, Statistics, And Documents

## Season Ratings

**Routes:** `/seasons`, `/seasons/<year>/`, plus legacy aliases `/season` and
`/season/<year>/`
**View:** `views/seasons.py:seasons`
**Templates:** `templates/seasons/seasons.html`,
`templates/players/players_table.html`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Title/description | Selected-year historical rating and tooltip | `seasons.html` |
| Year tabs | Every distinct year present in `Season` rows | `_get_available_years`; `_season_year_urls`; template |
| Search/filters | name/club search, historical club, age at December 31, sex | view filter helpers; template |
| Rating results | Reuses player table, but rows are `Season` objects and power is hidden | `players_table.html`; `app_filters.py` rating-item filters |
| Ranking/pagination | Rank within full selected-year result set; server-side pagination | view ranking/pagination helpers |

The route defaults to the latest stored season, or previous calendar year when
there are no season rows. It only shows rows with a player, a club, and positive
regular rating.

### Season Data Generation

Preferred workflow:

- `services/season_snapshots.py`
- `management/commands/generate_season_rating_snapshot.py`
- yearly cron in `components/web-api/conf/crontab.txt`
- operational guide in `docs/season-rating-snapshots.md`

The generator reads processed tournament membership result points for the
selected calendar year and writes `Season.rating`, `rating_b`, and
`rating_liga`.

There is also a legacy manual path in `Season.save_current_ratings()` and
`admin_actions/seasons.py`, which copies current player values instead of
recalculating the selected year's tournament results.

## Statistics

**Routes:** `/statistics/`, `/statistics/<year>/`
**View:** `views/statistics.py:statistics`
**Template:** `templates/statistics/statistics.html`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Period sidebar | Overall and every tournament year | view `periods`; template |
| Header/total | Selected period and total competitions | template |
| Countries | competition/team totals grouped by tournament country | view loop; template |
| Largest competitions | largest domestic competition by athletes/teams and averages | view aggregation; template |
| Clubs | organizer-club competition totals | view `tournaments_data['clubs']`; template |
| Organizers | main-organizer competition totals | view `tournaments_data['organizers']`; template |
| Disciplines | domestic counts grouped by minimum players per team | view; template |
| Venues | domestic counts grouped by exact place string | view; template |

Statistics are calculated in Python by iterating tournaments. The view queries
all tournaments directly rather than `Tournament.public_queryset()`, so old
unprocessed/auto-cancelled records remain included.

`players_all` is loaded but the current template does not render a player
statistics block.

## Documents

**Routes:** `GET /documents/` and
`GET /documents/<pk>/download/`
**Views:** `views/documents.py:documents`, `document_download`
**Template:** `templates/documents/documents.html`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Hero | Documents heading and description | template |
| Category sidebar | Active categories that contain active documents, with counts | `views/documents.py:documents`; template |
| Search/sort/view controls | Client-side name/notes search, date sort, card/line view persisted in local storage | template inline JavaScript |
| Year chips | Built client-side from rendered document dates | template inline JavaScript |
| Document list | Name, notes, category, date, extension, download action | template; `Document` properties |
| Empty/show-more state | Client-side filtering and 12-item progressive display | template inline JavaScript |
| Popular widget | Top five active documents by download count | view; template |
| Contact widget | Static federation email callout | template |

The download route:

1. Requires an active `Document`.
2. Atomically increments `download_count` with `F()`.
3. Redirects to the storage URL.

### Document Models And Admin

- `DocumentCategory`: unique code, display name/order, active flag.
- `Document`: name, notes, file, protected category relation, active flag,
  publication date, creation time, download count.
- Admin configuration is in `federation/admin.py`.
- File URL/storage behavior is in `federation/storage.py` and `api/settings.py`.

## Related Data Tables

| Feature | Tables |
| --- | --- |
| Seasons | `federation_season`, `federation_player`, `federation_club`, tournament membership source rows |
| Statistics | primarily `federation_tournament`, tournament/team memberships, players/clubs |
| Documents | `federation_documentcategory`, `federation_document` |

See [Database schema](../database-schema.md) for full fields and relationships.
