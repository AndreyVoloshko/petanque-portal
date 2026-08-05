# Per-Tournament Team Coach — Design

## Problem

There is no way to record who coaches a team at a given tournament. `Team`
(`federation/models/team.py:17`) is a reusable player roster shared across
tournaments — `Team.get_or_create_for_players()` looks up an existing team
with the same player set before creating a new one — so it has no notion of
"this tournament" at all. The only model that is genuinely scoped to a team's
participation in one specific tournament is `TeamTournamentMembership`
(`federation/models/tournament.py:524`), the through-table behind
`Tournament.teams`. That table currently carries placement, registration
date, and rating/power data, but nothing about a coach.

The federation already has a *coaching qualification* field
(`Player.coach_level`, `federation/models/player.py:86`) and a public
directory of certified coaches (`federation/views/coaches.py`), but neither
is tied to any team or tournament — they answer "who is a certified coach in
general," not "who coached this team at this tournament."

## Scope

In scope: an optional, per-tournament coach assignment for a registered
team — settable at self-service registration time, editable afterward in
Django admin, visible on the tournament page's team roster, and included in
the tournament JSON export.

Out of scope: any change to `Player.coach_level` (the certification
directory is unrelated and untouched), any restriction tying who can be
picked as coach to that certification, the CSV export
(`tournament_teams_export` with `?format=csv` — no natural coach column in a
one-row-per-player format), and any new post-registration self-service edit
flow (team registration remains a one-shot form; changing a coach after
registration is an admin-only action, same as changing the roster itself).

## Requirements (confirmed with stakeholder)

- **Coach identity**: any existing `Player` record, picked via the same
  select2 autocomplete (`api_players_list`) already used for player roster
  slots, arbiters, organizers, etc. Not restricted to players holding a
  `coach_level` certification, and not a free-text name — consistency with
  how every other tournament role (arbiter, main organizer, federation
  delegate) is modeled as a `Player` FK.
- **Validation**: no overlap restriction. A coach may already be a registered
  player on this team, on another team in the same tournament, or may coach
  more than one team in the same tournament. Mirrors how arbiters have no
  overlap checks against players today; playing-coaches are a normal
  petanque scenario.
- **Format scope**: available on every tournament format, including
  single-player ("individual") tournaments — a personal coach for an
  individual athlete is a normal scenario, not just a team concept. No
  conditional hiding based on `tournament_detail.is_single_player_format`.
- **Read API scope**: "tournament read API" is
  `GET /tournament/team_export/<id>?format=json` (`docs/api.md:87` — this
  project has no DRF/REST app; this hand-rolled export endpoint is the only
  JSON read surface for a tournament's teams). Coach is added there only,
  not to the CSV sibling.
- **Roster display**: a new "Coach" column/section next to "Captain" on the
  tournament page, shown only when a coach is set, following the existing
  desktop-table + mobile-card dual markup used for Captain.

## Approach

**Chosen: `coach` FK on `TeamTournamentMembership`.** Nullable
`ForeignKey(Player, on_delete=SET_NULL)`, following the exact shape and
`on_delete` behavior of `Tournament.main_organizer` /
`Tournament.federation_delegat` and of `ArbiterTournamentMembership.arbiter`
— the closest existing precedent for "an optional `Player` attached to one
row of tournament participation."

**Rejected: field on `Team`.** Would make a coach apply to the reusable
roster across every tournament that roster ever plays, contradicting "the
coach must be assigned per tournament, not permanently" — the explicit
requirement driving this feature.

**Rejected: reusing the national-teams `position` pattern.**
`PlayerNational_teamMembership.POSITIONS` (`federation/models/national_teams.py:33`)
already includes `'coach'`/`'main_coach'` choices as a multi-valued role
enum on a player-team join row. That model tree is for national squads (a
different `Team`-like concept entirely) and is multi-valued by design
(a squad can have several people in several roles). A tournament team has at
most one coach, so a dedicated FK column is simpler than introducing a
choices-based role table for a single optional value.

## Design

### 1. Model (`federation/models/tournament.py`)

Add to `TeamTournamentMembership`:

```python
coach = models.ForeignKey(
    'Player', verbose_name=_('Coach'),
    related_name='coached_team_memberships',
    on_delete=models.SET_NULL, null=True, blank=True,
)
```

New migration in `federation/migrations/` (next after `0076_club_is_active.py`).
No backfill — the field is nullable and starts empty for all existing rows.

### 2. Registration form (`federation/forms/registration_team_form.py`)

Add one field, built the same way as the player slots but unrequired and
outside the roster-position loop:

```python
self.fields['coach'] = forms.CharField(
    widget=forms.Select(attrs={
        'class': 'player-autocomplete',
        'data-minimum-input-length': PLAYER_SEARCH_MINIMUM_INPUT_LENGTH,
        'data-placeholder': _("Search coach by first or last name"),
    }),
    label=_("Coach"),
    required=False,
)
```

Same re-population-on-bind logic as the player fields (look up the selected
player, seed `field.widget.choices` so a validation-error round trip doesn't
lose the selection). `is_valid()` resolves it to `self.verified_coach_id`
(a single nullable id) alongside the existing `self.verified_player_ids` —
**not** run through the "player already registered in this tournament"
check, per the no-overlap-restriction requirement.

### 3. Registration view (`federation/views/register.py`)

`Tournament.add_team()` (`tournament.py:109`) gains an optional parameter:

```python
def add_team(self, team, coach=None):
    TeamTournamentMembership(tournament=self, team=team, coach=coach).save()
```

`register_team()` resolves `team_registration_form.verified_coach_id` to a
`Player` (or `None`) and passes it through:
`tournament.add_team(team, coach=coach)`.

### 4. Template (`federation/templates/register/team.html`)

One more field row, rendered after the player-field grid (not inside
`ordered_player_fields`, so it visually reads as a separate, optional
addition rather than another roster slot), reusing the same select2
initialization block already on the page (the `.player-autocomplete` class
selector already covers it — no new JS needed).

### 5. Admin (`federation/models/tournament.py`)

`TeamsTournamentMembershipInline` (`tournament.py:609`):

```python
class TeamsTournamentMembershipInline(RestrictedRelatedWidgetAdminMixin, admin.TabularInline):
    model = TeamTournamentMembership
    extra = 0
    autocomplete_fields = ['team', 'coach']
```

`RestrictedRelatedWidgetAdminMixin` already strips the add/delete shortcuts
from the widget generically, so no extra change is needed there. This is an
admin-only edit surface (self-service registration has no edit flow), so
this is also how a coach gets corrected or cleared after initial
registration.

No change needed to `save_formset` (`tournament.py:658`) — it only
recalculates tournament power on `TeamTournamentMembership` changes, and
coach has no bearing on power/rating math.

No new audit work: inline edits to `TeamTournamentMembership` fields
(`team`, `place_min`, `place_max`) already flow through Django's default
(unenriched) admin change log today — `RevertibleAuditAdminMixin` on the
Tournament admin only enriches changes to the top-level `Tournament` form,
not inline rows. `coach` behaves identically to those existing fields; no
special-casing required.

### 6. Tournament page (`federation/templates/tournaments/tournament_teams.html`)

Add a "Coach" column (desktop `<table>`, around line 44/126-132) and a
matching card section (mobile, around line 265/298-304), following the
exact pattern already used for `team.team.get_display_capitan`:

```django
{% if team.coach %}
    <a class="tournament-team-coach-name" href="{% url 'player' id=team.coach.pk %}">{{ team.coach.get_name }}</a>
{% else %}
    —
{% endif %}
```

(`team` here is a `TeamTournamentMembership` instance, as already iterated
in this template — `team.coach` is now a direct attribute access, no new
query given `select_related` already covers `team__team` and would be
extended to include `coach`.) Shown unconditionally (no
`is_single_player_format` gate), per the format-scope requirement — even
though the column header reads "Coach" regardless of format, the cell is
simply empty when unset, same as it will be for the vast majority of
existing/historical registrations.

`tournament()` view (`federation/views/tournaments.py:917`) — extend the
existing `select_related('team', ...)` on the `TeamTournamentMembership`
queryset (~line 994) to `select_related('team', 'coach', ...)` to avoid an
N+1 per row.

### 7. Read API (`federation/views/tournaments.py`, `tournament_teams_export`)

`?format=json` branch only (`tournaments.py:1117`). Add `'coach'` to each
team dict, reusing the existing `_player_brief()` helper already used for
`main_organizer`/`federation_delegat`/`arbiters`:

```python
'coach': _player_brief(team.coach) if team.coach else None,
```

Extend the queryset's `select_related('team')` (`tournaments.py:1043`) to
`select_related('team', 'coach')`.

`docs/api.md` — add `coach` to the JSON response example (`docs/api.md:118-150`)
directly under `date_registration`, documented as: present with the same
shape as `arbiters[]` entries (minus `is_main_arbiter`), or `null` when
unset.

### 8. Testing (`federation/tests.py`)

- `RegistrationTeamForm`: valid with `coach` omitted; valid with `coach`
  set to an existing player id; valid even when that player is also one of
  the selected roster players or already registered elsewhere in the
  tournament (confirms no overlap check was accidentally introduced).
- `register_team` view: POST with a coach persists
  `TeamTournamentMembership.coach`; POST without one leaves it `None`.
- Admin: saving `TeamsTournamentMembershipInline` with a `coach` value
  persists it; clearing it back to blank persists `None`; existing
  power-recalculation-on-save behavior is unaffected.
- `tournament_teams_export` JSON: a team with a coach includes the expected
  `coach` object; a team without one has `"coach": null`; CSV output is
  byte-identical to before (no coach column introduced).
- Tournament page rendering: a smoke check that a team with a coach set
  renders the coach name/link, and a team without one renders without
  error (both desktop and mobile-card branches).

### 9. Translations

New user-facing strings — the field label `_("Coach")`, the autocomplete
placeholder `_("Search coach by first or last name")`, and the "Coach"
column header — need entries in `locale/uk/LC_MESSAGES/django.po` and
`locale/en/LC_MESSAGES/django.po`, followed by `compilemessages` to
regenerate the `.mo` files (both committed together, matching existing
convention).

## Non-goals / explicitly out of scope

- No change to `Player.coach_level` or the certified-coaches directory.
- No restriction linking who can be picked as coach to any certification.
- No coach column in the CSV export.
- No post-registration self-service edit flow (admin-only correction, same
  as the rest of the roster).
- No change to rating/power calculation — coach is not a rating input.
