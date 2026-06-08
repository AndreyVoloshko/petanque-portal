# Home, Players, And Ratings

This area provides the landing page, current rating directories, public player
profiles, and the core current-rating calculation.

## Landing Page

**Route:** `GET /`
**View:** `views/main_page.py:main_page`
**Template:** `templates/main_page.html`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Hero | Federation message and links to registration/clubs | `templates/main_page.html` header block |
| Rating competitions | Up to 12 future rating tournaments | `main_page:_prepare_landing_tournaments`; `templates/main_page/tournaments_list.html` |
| Non-rating competitions | Up to 12 future non-rating domestic tournaments | same |
| Top-athlete tabs | Top three licensed men, women, veterans, and youth/espoir | `main_page`; `templates/main_page/players_list.html` |
| Tournament cards | Date, tags, venue, organizer, registered count, power | `templates/main_page/tournaments_list.html`; `utils/tournament_names.py`; tournament model |
| Player cards | Shared rating card with rank, points, power, club | `templates/players/_player_rating_card.html`; `utils/rankings.py` |

The view also computes top regular/B/senior lists that are currently not all
rendered by `main_page.html`.

## Current Rating / Player Directory

**Routes:**

- `/players/`: every player, regular current rating.
- `/players/licence/`: active licensed players.
- `/players/inclusive/`: inclusive players.
- `/players/<licence_filter>/b/`: B rating.
- `/players/<licence_filter>/liga/`: league rating.
- `/players/<licence_filter>/inclusive/`: inclusive rating.

**View:** `views/players.py:players`
**Templates:** `templates/players/players.html`,
`templates/players/players_table.html`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Title/description | Rating page heading | `players.html` |
| Search | Filters name, surname, patronymic, club names | `players.html`; `_get_player_filters`; `_apply_player_filters` |
| Club/age/sex filters | Server-side filters; age category is calculated in Python | view helpers and `PLAYER_AGE_CATEGORIES` |
| Results table | Ranking, athlete, points, optional power, sex, age, license, club, detail action | `players_table.html`; `templatetags/app_filters.py` |
| Mobile cards | Same row data in responsive card layout | `players_table.html` |
| Pagination/page size | Server-side page links and 25/30/50/100 page sizes | view pagination helpers; `players_table.html` |

Ranking places use competition ranking: tied rating values receive the same
place and the next place skips by the number of tied players. References:
`utils/rankings.py:rating_rank_map` and `attach_rating_positions`.

## Public Player Detail

**Route:** `GET /player/<id>`
**View:** `views/players.py:player`
**Template:** `templates/players/player.html`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Breadcrumbs | Home -> players -> player profile | template |
| Hero | Avatar, license badge, name, sport title, coach/arbiter/national-team chips | template; `Player`; `PlayerNational_teamMembership` lookup in view |
| Details card | Age category, gender, city, country, preferred position | template; `app_filters.py:player_age_category` |
| Club card | Current club logo/link, city/region, displayed member-since value | template; `Player.current_club` |
| Statistics card | Current rating place, points, power, current-year rating/international/total counts | view summary queries; template |
| Tournament table/cards | Past non-B tournaments, team roster, place, team/tournament power, earned points, rating relevance | `_build_player_tournament_rows`; `TeamTournamentMembership`; template |
| Tournament sorting/pagination | Client-side sort and pagination for rendered rows | inline JavaScript in `player.html`; `common/datatable_players_footer.html` |

The view also loads future, B, international, and season data into context.
The current redesigned template primarily renders `player_tournament_rows`,
which are built from past tournaments excluding B tournaments.

## Current Rating Data Model

Current values are denormalized onto `Player`:

| Rating family | Points | Power | Contributing tournament JSON |
| --- | --- | --- | --- |
| Regular | `current_rating` | `current_power` | `current_rating_tournaments` |
| B | `current_rating_b` | `current_power_b` | `current_rating_b_tournaments` |
| Inclusive | `current_rating_inclusive` | `current_power_inclusive` | `current_rating_inclusive_tournaments` |
| League | `current_rating_liga` | no dedicated power column | no contributing-tournament column |

Tournament-result values live on `TeamTournamentMembership`:
`rating_points`, `rating_power`, and `power`.

## Rating Calculation

Primary references:

- `models/player.py:Player.recalculate_ratings`
- `models/tournament.py:Tournament.recalculate_power`
- `models/tournament.py:Tournament.recalculate_ratings`
- `models/tournament.py:Tournament.calculate_basic_points`
- `models/tournament.py:Tournament.calculate_raw_team_rating_points`
- `models/tournament.py:TeamTournamentMembership.recalculate_power`
- `config/rating.py`

### Calculation Sequence

1. Team power is the average of the relevant current player-power field.
2. Tournament power is derived from top team powers and configured limits.
3. Tournament rating points are calculated from placement, tournament power,
   rating coefficient, and shared-place handling.
4. Closing a tournament triggers recalculation for players on every team.
5. Player current rating/power selects the best configured number of processed
   results within the configured recent time window.

Current configuration:

- Top 16 teams influence tournament power.
- Top 10 results influence player rating and power.
- Current player calculations use approximately the last 12 months.

### Eligibility

- `Player.get_actual_players_list()` requires active license state and a
  non-empty license number.
- Inclusive ranking uses all `is_inclusive=True` players.
- An inactive-license player has regular and B values zeroed by recalculation.
- The current implementation stores and displays league rating but does not
  update `current_rating_liga` in `Player.recalculate_ratings()`.

## Rating Triggers

| Trigger | Code |
| --- | --- |
| Weekly scheduled recalculation | `management/commands/recalculate_ratings.py`; `conf/crontab.txt` |
| Player admin action | `admin_actions/player.py:recalculate_ratings` |
| Tournament close | `Tournament.close_for_processing` -> memberships -> players |
| Registration-time provisional power | `Tournament.recalculate_power_on_registration` |

See [Operations and workflows](../operations-and-workflows.md) for the complete
tournament-processing sequence.

## High-Risk Change Notes

- Ratings are core business logic with little test coverage.
- Rating state is duplicated between tournament memberships and Player totals.
- Contributing tournament IDs are JSON stored in text fields, not relations.
- Template filters still calculate some ranks and query data during rendering.
- Age categories use current date on current rating pages, but December 31 of
  the selected year on season pages.
