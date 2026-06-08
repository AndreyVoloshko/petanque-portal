# Operations And Core Workflows

This document covers behavior that crosses pages, models, admin actions,
management commands, and scheduled jobs.

## Runtime And Safe Local Workflow

The existing Compose project is `petanque-portal`.

```bash
docker compose -p petanque-portal ps
docker compose -p petanque-portal logs petanque_portal_web_api
docker compose -p petanque-portal exec -T petanque_portal_web_api python manage.py check
```

Use `http://localhost:60102/` for browser verification. Do not reset, reseed, or
replace `petanque_portal_db` / `petanque_db`; it contains production-derived
data. After runtime code changes:

```bash
docker compose -p petanque-portal up -d --build petanque_portal_web_api
```

References: `docker-compose.yml`, `components/web-api/Dockerfile.service`,
`components/web-api/conf/supervisor-app.conf`,
`components/web-api/application/gunicorn_start`.

## Tournament Registration Workflow

```text
GET/POST /register/team/<tournament_id>
  -> RegistrationTeamForm dynamically builds player fields
  -> validates every Player and rejects already-registered participants
  -> Team.get_or_create_for_players reuses or creates Team + memberships
  -> Tournament.add_team creates TeamTournamentMembership
  -> Tournament.recalculate_power_on_registration updates displayed power
```

References:

- `views/register.py:register_team`
- `forms/registration_team_form.py:RegistrationTeamForm`
- `models/team.py:Team.get_or_create_for_players`
- `models/tournament.py:Tournament.add_team`
- `models/tournament.py:Tournament.recalculate_power_on_registration`

Important behavior:

- The first selected player becomes captain.
- The route is public; it does not require login.
- Registration availability is displayed using
  `Tournament.is_registration_opened()`.
- Team reuse is based on exact player membership and captain state.
- There is no database uniqueness constraint preventing duplicate tournament/team
  memberships; validation and application behavior carry that responsibility.

## Tournament Result Processing Workflow

Tournament processing is controlled primarily through Django admin actions:

```text
mark ready
  -> recalculate team/tournament power
  -> calculate rating points for placed teams
  -> close processing
  -> recalculate ratings for players in every registered team
```

| Step | Domain methods | Admin action |
| --- | --- | --- |
| Mark ready | `Tournament.mark_as_ready_for_processing` | `admin_actions/tournament.py:mark_as_ready_for_processing` |
| Recalculate power | `Tournament.recalculate_power`; `TeamTournamentMembership.recalculate_power` | `recalculate_power` |
| Calculate result points | `Tournament.recalculate_ratings`; `calculate_basic_points`; `calculate_raw_team_rating_points` | `recalculate_ratings` |
| Close and propagate | `Tournament.close_for_processing`; `TeamTournamentMembership.recalculate_ratings_for_players` | `finish_processing` |
| Full sequence | all methods above | `full_power_and_rating_processing` |
| Reset calculations/state | `Tournament.erase_rating_points_and_powers` | `erase_rating_points_and_powers` |

Guard conditions live in `models/tournament.py`: foreign tournaments cannot be
processed for rating; tournament must be marked ready; closed tournaments reject
further processing; a finished date, teams, and positive power are required.

The tournament detail route also allows authorized organizers/superusers to edit
places and final-protocol notes. Those mutations live in
`views/tournaments.py:tournament`, not in the admin actions.

## Current Rating Workflow

Current rating settings are in `federation/config/rating.py`:

- Tournament power uses the top 16 team powers.
- Player rating and power use the top 10 qualifying results.
- Only processed results from the last 12 approximate months (`30 * 12` days)
  are considered.

`Player.recalculate_ratings()`:

1. Finds the player's processed past tournaments in the time window.
2. Separates regular, B, and inclusive results.
3. Selects the highest 10 rating-point results and power results in each group.
4. Writes totals to the player's current rating/power columns.
5. Stores contributing regular/B/inclusive tournament IDs as JSON text.
6. Zeros regular and B values for inactive-license players; inclusive values can
   remain for inclusive players.

`current_rating_liga` exists and is displayed by league routes, but
`Player.recalculate_ratings()` does not currently recalculate it. Treat that as
an explicit legacy gap before changing league behavior.

References:

- `models/player.py:Player.recalculate_ratings`
- `models/tournament.py:Tournament.recalculate_ratings`
- `models/tournament.py:TeamTournamentMembership.recalculate_power`
- `utils/rankings.py`
- `management/commands/recalculate_ratings.py`
- `admin_actions/player.py`

## Season Snapshot Workflow

Historical ratings are rows in `federation_season`, not calculated dynamically
from current `Player` values when the season page loads.

The preferred generator is:

```bash
docker compose -p petanque-portal exec -T petanque_portal_web_api \
  python manage.py generate_season_rating_snapshot --year 2025
```

It reads processed `TeamTournamentMembership` rows in the calendar year and
calculates regular, B, and league totals. `--replace` updates existing rows and
deletes stale rows, so use it deliberately.

References:

- `services/season_snapshots.py`
- `management/commands/generate_season_rating_snapshot.py`
- `docs/season-rating-snapshots.md`
- Legacy/manual snapshot path: `models/season.py:Season.save_current_ratings`
  and `admin_actions/seasons.py`

## Scheduled Jobs

`components/web-api/conf/crontab.txt` schedules:

| Schedule | Command | Effect |
| --- | --- | --- |
| Wednesday 00:00 | `manage_cron.py recalculate_ratings` | Recalculates current licensed-player ratings |
| Thursday 02:00 | `manage_cron.py dbbackup` | Runs Django DB backup |
| January 1 00:05 | `manage_cron.py generate_season_rating_snapshot --previous-year` | Generates previous calendar-year season snapshot |

`manage_cron.py` copies environment variables from PID 1 before executing
`manage.py`, because cron starts with a minimal environment.

## Admin Area

Registered domain models are centralized in `federation/admin.py`; specialized
admin classes are located beside their models.

| Model area | Important admin behavior |
| --- | --- |
| Players | Recalculate/erase ratings, activate/deactivate/erase licenses |
| Tournaments | Inline arbiters and teams, processing actions, restricted add permission |
| Teams | Inline player membership/captain management |
| National teams/departments | Inline player membership and roles |
| Seasons | Save current ratings legacy action |
| Documents | Category/filter/search, download count read-only |

Tournament creation permission is stricter than normal superuser status:
`permissions.py:can_create_tournament` requires an active authenticated
superuser whose `(id, username)` is in a hardcoded allowlist.

## Storage, Email, And External Services

| Concern | Implementation |
| --- | --- |
| Local static/media | File-system storage when no S3 bucket is configured |
| Production static/media | S3 storage classes in `federation/storage.py` |
| Uploaded names | `MediaStorage` replaces names with an MD5 of current time plus extension |
| Confirmation email | `utils/email.py:send_confirmation_email`, Django email backend settings |
| Registration bot check | reCAPTCHA v3-style score verification in `utils/autocaptcha.py` |
| Country/language selection | `middleware.py:InitialLanguageMiddleware` and `django-countries` |

## Verification Checklist For High-Risk Changes

1. Run `python manage.py check` inside the existing web container.
2. Add focused tests before changing rating or tournament-processing math.
3. Test public and authorized views separately.
4. Confirm mutations against disposable records, not production-derived records
   that matter.
5. Verify relevant pages at `http://localhost:60102/`.
6. Review web logs for errors.
7. For schema changes, compare models, migration operations, and the live schema
   described in [database-schema.md](database-schema.md).
