# Clubs And Federation Registries

This area documents clubs, club detail, the shared federation registry pages,
and records.

## Clubs List

**Route:** `GET /clubs/`
**View:** `views/clubs.py:clubs`
**Templates:** `templates/clubs/clubs.html`, `templates/clubs/clubs_table.html`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Title | Clubs heading and description | `clubs.html` |
| Filters | Search, city, creation year, sort | `clubs.html`; `_get_club_filters`; `_apply_club_filters` |
| Ranking/aggregates | Total active-player rating, average rating, active-player count | `_clubs_queryset` annotations |
| Results table/mobile cards | rank, identity/logo, points, average, city/map, founded date, president, athletes | `clubs_table.html` |
| Empty state | No matching clubs | `clubs_table.html` |
| Pagination/page size | Server-side pagination, 25/50/100 page sizes | view helpers; `clubs_table.html` |

Sort modes: total rating, athlete count, average rating, name, or newest club.

## Club Detail

**Route:** `GET /club/<id>`
**View:** `views/clubs.py:club`
**Template:** `templates/clubs/club.html`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Breadcrumbs | Home -> clubs -> club | template |
| Hero/identity | Logo, full/short name, city/country, social links | template; `Club`; `app_filters.py:social_url` |
| Hero metrics | athlete count, founded date, club rating place | view `club_stats`; template |
| President | Shared player rating card or empty state | template; `Club.president` |
| Club indicators | total/average rating, average power, national-team athlete count, candidate-title count | view aggregates; template |
| Athlete roster | Shared player cards with client-side search, sex/category filter, and sort | template inline JavaScript; `Player.current_club` query |

Club rating uses licensed players for aggregates. The roster includes all
players whose current club is the club.

## Shared Federation Registry Page

The following routes all render
`templates/common/title_registry_page.html`:

| Route | Group source | View |
| --- | --- | --- |
| `/arbiters/` | `Player.ARBITER_CATEGORY` / `Player.arbiter_level` | `views/arbiters.py` |
| `/coaches/` | `Player.COACH_CATEGORY` / `Player.coach_level` | `views/coaches.py` |
| `/sport_titles/` | `Player.SPORT_TITLES` / `Player.sport_title` | `views/sport_titles.py` |
| `/national_teams/` and `/national_teams/<team_id>/` | National teams and position memberships | `views/national_teams.py` |
| `/departments/` | Departments and ordered role memberships | `views/departments.py` |

Shared data shaping lives in `views/title_registry.py`.

### Shared Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Header | Route-specific title/subtitle | `title_registry.py:ROUTE_CONFIG`; shared template |
| Category sidebar/tabs | Categories/teams/departments with short labels | `title_registry_context`; `_mark_active_group`; shared template |
| Group header | Group label and player count | shared template |
| Player card grid | Shared player cards with route-specific status badges | shared template; `_player_rating_card.html` |
| Empty state | No groups with players | shared template |

### Registry Data Models

- Arbiters, coaches, and sport titles are fields on `Player`.
- National teams use `National_team` and
  `PlayerNational_teamMembership.position`.
- Departments use `Department` and `PlayerDepartmentMembership`, including
  `role`, optional description, and explicit order.

## Records

**Route:** `GET /records/`
**View:** `views/records.py:records`
**Templates:** `templates/records/records.html`,
`templates/records/records_table.html`

Each card displays record name/value, optional date and notes, and optionally a
linked player or linked club. Data is managed through Django admin and stored in
`federation_record`.

## Navigation And Administration

All these pages are linked from the Federation menu in
`templates/common/menu.html`.

Operational data is managed through `/admin/`:

- `Club` with city/president autocomplete.
- `National_team` with player membership inline.
- `Department` with ordered role membership inline.
- `Record` with default model admin.
- Arbiter, coach, and sport-title values through `Player` admin.

References: `federation/admin.py` and model admin classes beside each model.

## Relationship Notes

- `Player.current_club` and `Club.president` create a circular logical
  relationship, both nullable.
- Club aggregates use current-club assignment, not historical club membership.
- The live database contains an untracked historical
  `federation_playerclubmembership` table, but current checked-in code does not
  read it. See [Database schema](../database-schema.md#live-only-schema-drift).
