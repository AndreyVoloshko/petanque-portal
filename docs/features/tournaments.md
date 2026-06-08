# Tournaments

Tournaments connect clubs, organizers, delegates, arbiters, teams, players,
ratings, registration, exports, and historical results. Most behavior is in
`federation/views/tournaments.py` and `federation/models/tournament.py`.

## Tournament List

**Routes:** `/tournaments/`, `/tournaments/<date_filter>/`,
`/tournaments/<date_filter>/<type_filter>/`
**View:** `views/tournaments.py:tournaments`
**Templates:** `templates/tournaments/tournaments.html`,
`templates/tournaments/tournaments_table.html`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Title/action | Page title; create button only for users allowed by hardcoded permission | template; `permissions.py:can_create_tournament`; admin add route |
| Period tabs | Future, ongoing, past counts and URLs | `_get_period_tabs`; `_count_tournaments_for_filters` |
| Rating/foreign toggles | Filters rating-only or foreign competitions | template forms; `_apply_rating_filter`; `_apply_foreign_filter` |
| Search and filters | Name/metadata search, inferred format/category, venue, organizer club | `_get_tournament_filters`; `_row_matches_filters`; `utils/tournament_names.py` |
| Results table/cards | Responsive desktop/tablet/mobile renderings of date, title, tags, venue, organizer, registration/status, teams, power, actions | `tournaments_table.html`; `_build_tournament_row` |
| Empty state | Context-aware no-results message | `_empty_state` |
| Pagination/sort | Date order and responsive page sizes | view pagination helpers; template JavaScript |

### Query Parameters

| Parameter | Values/meaning |
| --- | --- |
| `period` | `future`, `ongoing`, `past` |
| `type` | `all`, `rating`, `non_rating` |
| `foreign` | truthy flag |
| `q` | tokenized search across title, format, venue, country, organizer |
| `format` | inferred UI keys such as `tete`, `doublets`, `triplets`, `shooting`, `clubs`, `supermelee` |
| `category` | inferred audience key such as `men`, `women`, `mixed`, `juniors`, `veterans`, `open` |
| `place`, `club` | exact venue or organizer-club ID |
| `sort` | `date_asc`, `date_desc` |
| `per_page` | 5, 25, 30, or 50 |

Public lists use `Tournament.public_queryset()`, which excludes old,
unprocessed tournaments after the automatic-cancel cutoff.

## Tournament Detail

**Route:** `GET/POST /tournament/<id>`
**View:** `views/tournaments.py:tournament`
**Template:** `templates/tournaments/tournament.html`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Breadcrumbs | Home -> competitions -> current title | `tournament.html` |
| Summary hero | Format/audience/openness/rating chips, normalized title, date/time | `templates/tournaments/tournament_summary.html`; `_build_tournament_detail`; `utils/tournament_names.py` |
| Summary metrics | Venue/country/map, organizer, registration count, tournament power, rating coefficient | summary partial; `_build_tournament_row` |
| Participation card | format, category, team size/limit, fees | summary partial; `Tournament` |
| Additional information/actions | status/deadline, register/results/regulations/export actions, notes | summary partial; `_tournament_status_data` |
| Organizers and arbiters | Organizer, delegate, head/other arbiters as player cards | `tournament_delegations.html`; `_tournament_person_card.html`; `ArbiterTournamentMembership` |
| Teams/participants | Place, captain/participant, athletes, rating earned, team power, registration date, remove action | `tournament_teams.html`; `TeamTournamentMembership`; template filters |
| Organizer notes tab | Final-protocol notes editor for authorized tournament managers | `tournament.html`; POST branch in `views/tournaments.py:tournament` |

Single-player formats change labels from teams/captain to participants and are
detected by inferred format or min/max team size.

### Detail POST Actions

The same CSRF-exempt view handles several mutations:

| POST field | Behavior | Authorization |
| --- | --- | --- |
| `meta` | Writes raw `Tournament.meta`, returns JSON | No explicit auth check |
| `tournament_notes_content` | Escapes and saves final protocol notes | Authenticated tournament manager |
| `delete_team_id` | Deletes tournament membership | Authenticated user with team access |
| `teams` | JSON array updates min/max places | Authenticated tournament manager |

Authorization rules live in
`Tournament.is_user_has_admin_access_to_tournament()` and
`TeamTournamentMembership.is_user_has_admin_access_to_team()`. The unauthenticated
`meta` mutation is a known security-sensitive behavior; see
`docs/audit/security.md`.

## Team Registration

**Route:** `GET/POST /register/team/<tournament_id>/`
**View/form/template:** `views/register.py:register_team`,
`forms/registration_team_form.py`, `templates/register/team.html`

The page contains a dynamic player-selection form, a tournament summary, and a
missing-player registration callout. See
[Authentication, registration, and profile](authentication-registration-profile.md#team-registration)
and [Operations and workflows](../operations-and-workflows.md#tournament-registration-workflow).

## Calendar

**Route:** `GET /calendar/`
**Template:** `templates/tournaments/calendar.html`

The page is almost entirely client-side FullCalendar configuration. It requests
events from `/api/tournaments/list/` with visible range `start` and `end`
parameters. Event CSS classes represent rating, league, B, and category state.

References: `views/tournaments.py:tournaments_calendar`,
`views/api.py:tournaments_list`, calendar static assets.

## Team Export

**Route:** `GET /tournament/team_export/<id>?format=<html|csv|json>`
**View:** `views/tournaments.py:tournament_teams_export`

| Format | Purpose | Rendering |
| --- | --- | --- |
| HTML/default | Print-friendly complete team list | `templates/tournaments/pure_teams_list.html` |
| CSV | External draw/import format, semicolon delimiter | Built directly in view |
| JSON | External integration with tournament, organizer, arbiter, team, club, player, rating/rank data | Built directly in view |

The export chooses player rating field by tournament type in
`_export_player_rating_field`. A team-level club is exported only when every
player currently belongs to the same club.

See [API reference](../api.md) for JSON and CSV details.

## Final Protocol

**Route:** `GET /tournament/tournament_protocol/<id>`
**View:** `views/tournaments.py:tournament_protocol`
**Template:** `templates/tournaments/tournament_protocol.html`

The view redirects to tournament detail unless processing is closed. Blocks:

- Federation/protocol heading.
- Tournament identity, dates, organizer, and venue.
- Organizer/delegate/arbiter roles.
- Team/player totals.
- Top four result rows and link to complete team list.
- Final notes and incident area.
- Signature placeholders.

## Tournament Model And Relations

`Tournament` stores classification flags, dates, registration limits, rating
state, organizers, files, notes, and processing state.

```text
Club 0..1 -> many Tournament (organizer_club)
Player 0..1 -> many Tournament (main_organizer)
Player 0..1 -> many Tournament (federation_delegat)
Tournament many <-> many Player through ArbiterTournamentMembership
Tournament many <-> many Team through TeamTournamentMembership
Team many <-> many Player through PlayerTeamMembership
```

Full fields and relation semantics are in [Database schema](../database-schema.md).

## Tournament Display Metadata

The stored `Tournament.name` is not always the displayed title.
`utils/tournament_names.py`:

- Normalizes spacing and punctuation.
- Adds year and inferred format when absent.
- Extracts format and audience tags from names.
- Provides search matching against normalized display names.

List/detail helpers in `views/tournaments.py` additionally infer country,
foreign status, place label, openness, registration status, cancellation, and
single-player presentation.

## Processing And Rating

Tournament power, result points, closure, and player-rating propagation are
documented in [Operations and workflows](../operations-and-workflows.md).
Do not change those methods as presentation-only helpers; they mutate persistent
rating state.
