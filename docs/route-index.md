# Route Index

The top-level URL configuration is
`components/web-api/application/api/urls.py`. It mounts Django admin, language
switching, static-file serving in local mode, and all routes from
`components/web-api/application/federation/urls.py`.

All routes below are relative to the site root. The local root is
`http://localhost:60102/`.

## Shared Page Blocks

Most HTML pages extend `templates/common/page_base.html` or
`templates/common/page_with_header.html`.

| Block | Behavior | Code references |
| --- | --- | --- |
| HTML head and shared assets | Bootstrap, jQuery, DataTables, calendar assets, styles, metadata | `templates/common/head.html`, `templates/common/foot.html` |
| Main navigation | Federation/competition/rating menus, auth menu, superuser admin link | `templates/common/menu.html` |
| Global search | Autocomplete across players, clubs, and public tournaments | `templates/common/menu.html`; `views/api.py:players_clubs_and_tournaments_list`; `utils/tournament_names.py:tournament_display_name_matches` |
| Language selection | Posts to Django `set_language`; first visit may be selected from geo headers | `templates/common/menu.html`; `middleware.py:InitialLanguageMiddleware`; `api/settings.py` |
| Cookie consent | Sets `gdpr_agree=1`, or redirects the visitor away | `templates/common/header.html` |
| Flash messages | Renders Django messages from registration/profile/tournament/admin flows | `templates/common/messages.html` |
| Footer | Federation link, current year, development credit | `templates/common/footer.html` |
| Shared player card | Reused by landing, club detail, and registry pages | `templates/players/_player_rating_card.html`; `templatetags/app_filters.py` |

## Public HTML Routes

| Route | View | Primary template | Feature documentation |
| --- | --- | --- | --- |
| `GET /` | `views/main_page.py:main_page` | `templates/main_page.html` | [Home, players, and ratings](features/home-players-ratings.md) |
| `GET /clubs/` | `views/clubs.py:clubs` | `templates/clubs/clubs.html` | [Clubs and federation registries](features/clubs-and-federation.md) |
| `GET /club/<id>` | `views/clubs.py:club` | `templates/clubs/club.html` | [Clubs and federation registries](features/clubs-and-federation.md) |
| `GET /players/` | `views/players.py:players` | `templates/players/players.html` | [Home, players, and ratings](features/home-players-ratings.md) |
| `GET /players/<licence_filter>/` | `views/players.py:players` | `templates/players/players.html` | [Home, players, and ratings](features/home-players-ratings.md) |
| `GET /players/<licence_filter>/<rating_filter>/` | `views/players.py:players` | `templates/players/players.html` | [Home, players, and ratings](features/home-players-ratings.md) |
| `GET /player/<id>` | `views/players.py:player` | `templates/players/player.html` | [Home, players, and ratings](features/home-players-ratings.md) |
| `GET /tournaments/` | `views/tournaments.py:tournaments` | `templates/tournaments/tournaments.html` | [Tournaments](features/tournaments.md) |
| `GET /tournaments/<date_filter>/` | `views/tournaments.py:tournaments` | same | [Tournaments](features/tournaments.md) |
| `GET /tournaments/<date_filter>/<type_filter>/` | `views/tournaments.py:tournaments` | same | [Tournaments](features/tournaments.md) |
| `GET/POST /tournament/<id>` | `views/tournaments.py:tournament` | `templates/tournaments/tournament.html` | [Tournaments](features/tournaments.md) |
| `GET /calendar/` | `views/tournaments.py:tournaments_calendar` | `templates/tournaments/calendar.html` | [Tournaments](features/tournaments.md) |
| `GET /national_teams/` | `views/national_teams.py:national_teams` | `templates/national_teams/national_teams.html` | [Clubs and federation registries](features/clubs-and-federation.md) |
| `GET /national_teams/<team_id>/` | same | same | [Clubs and federation registries](features/clubs-and-federation.md) |
| `GET /arbiters/` | `views/arbiters.py:arbiters` | `templates/arbiters/arbiters.html` | [Clubs and federation registries](features/clubs-and-federation.md) |
| `GET /coaches/` | `views/coaches.py:coaches` | `templates/coaches/coaches.html` | [Clubs and federation registries](features/clubs-and-federation.md) |
| `GET /sport_titles/` | `views/sport_titles.py:sport_titles` | `templates/sport_titles/sport_titles.html` | [Clubs and federation registries](features/clubs-and-federation.md) |
| `GET /departments/` | `views/departments.py:departments` | `templates/departments/departments.html` | [Clubs and federation registries](features/clubs-and-federation.md) |
| `GET /records/` | `views/records.py:records` | `templates/records/records.html` | [Clubs and federation registries](features/clubs-and-federation.md) |
| `GET /documents/` | `views/documents.py:documents` | `templates/documents/documents.html` | [Seasons, statistics, and documents](features/seasons-statistics-documents.md) |
| `GET /documents/<pk>/download/` | `views/documents.py:document_download` | redirect to file | [Seasons, statistics, and documents](features/seasons-statistics-documents.md) |
| `GET /seasons`, `/season` | `views/seasons.py:seasons` | `templates/seasons/seasons.html` | [Seasons, statistics, and documents](features/seasons-statistics-documents.md) |
| `GET /seasons/<year>/`, `/season/<year>/` | same | same | [Seasons, statistics, and documents](features/seasons-statistics-documents.md) |
| `GET /statistics/` | `views/statistics.py:statistics` | `templates/statistics/statistics.html` | [Seasons, statistics, and documents](features/seasons-statistics-documents.md) |
| `GET /statistics/<year>/` | same | same | [Seasons, statistics, and documents](features/seasons-statistics-documents.md) |

`licence_filter` recognizes `licence` and `inclusive`. `rating_filter`
recognizes `b`, `liga`, and `inclusive`. Tournament route aliases are retained
for old links, but query parameters are the primary current filtering interface.

## Registration And Authentication Routes

| Route | Method/auth | View/template | Purpose |
| --- | --- | --- | --- |
| `/register/player/` | GET/POST, public | `views/register.py:register_player`; `templates/register/player.html` | Creates `auth_user`, `Player`, optional `EmailConfirmation`, logs user in |
| `/register/team/<tournament_id>/` | GET/POST, public | `views/register.py:register_team`; `templates/register/team.html` | Creates/reuses `Team`, creates `TeamTournamentMembership` |
| `/login/` | GET/POST, public | `views/login.py:application_login`; `templates/login.html` | Username or email login |
| `/logout/` | GET | `views/logout.py:application_logout` | Ends session and redirects home |
| `/profile/` | GET/POST, login required | `views/profile.py:profile`; `templates/profile.html` | Edits player profile/email or changes password |
| `/email/prompt/` | GET/POST, login required | `views/email_confirm.py:email_prompt`; `templates/email_confirm/prompt.html` | Starts or resends email confirmation |
| `/email/confirm/<uuid:token>/` | GET, public | `views/email_confirm.py:email_confirm` | Confirms email within 24 hours |
| `/password-reset/` | GET/POST, public | `views/password_reset.py:CustomPasswordResetView`; `templates/password_reset/request.html` | Requests password reset for confirmed/legacy email |
| `/password-reset/done/` | GET | Django auth view; `templates/password_reset/done.html` | Email-sent confirmation |
| `/password-reset/<uidb64>/<token>/` | GET/POST | `CustomPasswordResetConfirmView`; `templates/password_reset/confirm.html` | Sets new password |
| `/password-reset/complete/` | GET | Django auth view; `templates/password_reset/complete.html` | Reset-complete confirmation |

See [Authentication, registration, and profile](features/authentication-registration-profile.md).

## Exports And Protocol

| Route | Output | Code |
| --- | --- | --- |
| `GET /tournament/team_export/<id>?format=html` | Print-oriented registered-team page | `views/tournaments.py:tournament_teams_export`; `templates/tournaments/pure_teams_list.html` |
| same with `format=csv` | Semicolon-delimited external draw file | `views/tournaments.py:tournament_teams_export` |
| same with `format=json` | Tournament/team/player JSON | `views/tournaments.py:tournament_teams_export`; documented in [API reference](api.md) |
| `GET /tournament/tournament_protocol/<id>` | Printable final protocol; redirects until processing is closed | `views/tournaments.py:tournament_protocol`; `templates/tournaments/tournament_protocol.html` |

## JSON/API Routes

| Route | Method/auth | Consumer | Code |
| --- | --- | --- | --- |
| `/api/tournaments/list/` | GET, public | FullCalendar on `/calendar/` | `views/api.py:tournaments_list` |
| `/api/players_clubs_and_tournaments/list/` | GET, public | Global navigation search | `views/api.py:players_clubs_and_tournaments_list` |
| `/api/players_list/list/` | GET, public | Team registration Select2 and registration duplicate search | `views/api.py:players_list` |
| `/api/tournament/results/` | POST, `Authorization` header API password | External result submitter | `views/api.py:submit_tournament_results` |

Detailed request/response examples are in [API reference](api.md).

## Admin And Framework Routes

| Route | Purpose | References |
| --- | --- | --- |
| `/admin/` | Django admin for all registered domain models and actions | `api/urls.py`; `federation/admin.py`; model admin classes; `admin_actions/` |
| `/i18n/setlang/` | Django language switch endpoint | `api/urls.py`; `templates/common/menu.html` |
| `/static/<path>` | Local debug static serving when `STATIC_URL == '/static/'` | `api/urls.py`; `api/settings.py` |
| `/media/<path>` | Local media route appended by `federation/urls.py` | `federation/urls.py`; `api/settings.py` |

## Error Pages

`templates/404.html` and `templates/500.html` exist. Custom handlers are defined
at the bottom of `federation/urls.py`, but they use an obsolete
`context_instance` argument and are called out as broken in
[the architecture audit](audit/architecture.md).
