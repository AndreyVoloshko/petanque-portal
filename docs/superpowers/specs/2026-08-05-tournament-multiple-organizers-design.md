# Multiple Tournament Organizers — Design

## Problem

`Tournament.main_organizer` (`federation/models/tournament.py:76`) is a single
nullable `Player` FK — there is no way to record additional people who help
organize a tournament. The only existing "multiple people attached to one
tournament" pattern is `ArbiterTournamentMembership`
(`federation/models/tournament.py:591`), a through-table between `Tournament`
and `Player` with a boolean `is_main_arbiter` flag. No equivalent exists for
organizers.

## Scope

In scope: an admin-managed list of co-organizers per tournament, separate
from (and in addition to) the existing `main_organizer` field, with a `role`
attribute that today only has one possible value but is built to accept more
later without a schema change. Displayed on the tournament delegations page
next to the existing main organizer card.

Out of scope: any change to `main_organizer`, `organizer_club`, or
`federation_delegat` (all untouched); any change to
`is_user_has_admin_access_to_tournament` or
`TeamTournamentMembership.is_user_has_admin_access_to_team` (co-organizers do
not get tournament-admin rights); any self-service (non-admin) editing
surface; the `?output_format=json` tournament export; and
`tournament_protocol.html` (the official document).

## Requirements (confirmed with stakeholder)

- **Relationship to `main_organizer`**: additive, not a replacement. The
  "main one" stays a distinct, separately-displayed field; co-organizers are
  "other people, except that one."
- **Permissions**: co-organizers are view/credit only. They do not gain
  admin rights over the tournament (editing notes/teams, viewing insurance
  warnings) — only `main_organizer` and superusers keep that, unchanged.
- **Editing**: Django admin only, via an inline on the `Tournament` admin
  page — same as how `main_organizer`, `federation_delegat`, and arbiters are
  managed today. No new public-facing form.
- **Role**: modeled as a `CharField(choices=...)` seeded with a single
  `('organizer', _('Organizer'))` value, following the existing plain-tuple
  choices style used by `PlayerNational_teamMembership.POSITIONS`,
  `Player.GENDER_CHOICES`, etc. (not `models.TextChoices`, which isn't used
  anywhere else in this codebase). A future second role is then just another
  tuple entry — no migration to add the column itself.
- **Display**: `tournament_delegations.html` only, as additional person
  cards next to the main organizer card, using the same
  `_tournament_person_card.html` partial already used for arbiters.
- **Duplicates**: `unique_together` on `(tournament, organizer)` prevents the
  same player being added twice as a co-organizer. No cross-table validation
  against `main_organizer` — a player can technically be both `main_organizer`
  and a co-organizer row (they'd then show up as two cards); this is an
  unlikely admin mistake, not worth a `clean()` guard.

## Approach

**Chosen: new `OrganizerTournamentMembership` through-table**, following the
exact shape of `ArbiterTournamentMembership` (`Tournament` FK +  `Player` FK)
plus a `role` choices field for the future-roles requirement.

**Rejected: reuse/extend `ArbiterTournamentMembership`.** Organizers and
arbiters are conceptually distinct roles with independent lifecycles (an
arbiter is not an organizer and vice versa); overloading one table with a
`type` discriminator would complicate the existing arbiter-only admin inline
and queries for no benefit.

**Rejected: boolean flag instead of `role` choices** (mirroring arbiters'
`is_main_arbiter`). Rejected because the stated requirement is explicitly
that the role "may be different in future" — a boolean can only ever
distinguish two states, while a choices field accepts new roles by adding a
tuple entry.

**Rejected: `models.TextChoices` for the role enum.** Confirmed with
stakeholder — plain tuple choices matches every existing choices field in
this codebase; introducing the class-based style for one field would be an
inconsistent one-off.

## Design

### 1. Model (`federation/models/tournament.py`)

Add near `ArbiterTournamentMembership`, before the "Classes for admin"
section:

```python
# Organizers to Tournaments relation
class OrganizerTournamentMembership(models.Model):
    ROLES = (
        ('organizer', _('Organizer')),
    )
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, verbose_name="Турнір", null=True)
    organizer = models.ForeignKey(Player, on_delete=models.CASCADE, verbose_name="Організатор", null=True)
    role = models.CharField(_('Role'), max_length=50, choices=ROLES, default='organizer')

    class Meta:
        unique_together = ('tournament', 'organizer')
        verbose_name = 'Організатор турніру'
        verbose_name_plural = 'Організатори турніру'
```

New migration in `federation/migrations/` (next after
`0077_teamtournamentmembership_coach.py`). No backfill — new table, starts
empty.

### 2. Admin (`federation/models/tournament.py`)

New inline next to `ArbiterTournamentMembershipInline`:

```python
class OrganizerTournamentMembershipInline(RestrictedRelatedWidgetAdminMixin, admin.TabularInline):
    model = OrganizerTournamentMembership
    extra = 0
    autocomplete_fields = ['organizer']

    class Meta:
        verbose_name = 'Організатори турніру'
        verbose_name_plural = 'Організатори турніру'
```

Registered first in `ArbiterTeamTournamentAdminInline.inlines`:

```python
inlines = (OrganizerTournamentMembershipInline, ArbiterTournamentMembershipInline, TeamsTournamentMembershipInline,)
```

(Ordered first to match the "Organizers and arbiters" heading order on the
public page.) No change to `has_add_permission`, `save_formset`, or
`autocomplete_fields` on the parent admin — those are unaffected by this
inline.

### 3. View (`federation/views/tournaments.py`, `tournament()`)

Next to the existing `arbiters` query (~line 993):

```python
organizers = OrganizerTournamentMembership.objects.filter(tournament=tournament).select_related('organizer', 'organizer__current_club')
```

Added to the render context (~line 1017) as `'organizers': organizers`.

### 4. Template (`federation/templates/tournaments/tournament_delegations.html`)

New loop inserted between the `main_organizer` card and the `arbiters` loop:

```django
{% for membership in organizers %}
    {% include "tournaments/_tournament_person_card.html" with person=membership.organizer role_label=membership.get_role_display role_icon="bi-person-check" card_class="tournament-person-card-organizer" %}
{% endfor %}
```

Using `membership.get_role_display` (rather than a static translated label
like the existing `main_organizer_label`/`arbiter_label` constants) means a
future second `ROLES` entry displays correctly with no template change.

The `{% if tournament.main_organizer or arbiters %}` / empty-state guard
(line 12) extends to `{% if tournament.main_organizer or organizers or arbiters %}`
so the section still renders correctly when only co-organizers exist.

### 5. Testing (`federation/tests.py`)

- Model: creating an `OrganizerTournamentMembership` persists correctly;
  a duplicate `(tournament, organizer)` pair raises an integrity error.
- View: `tournament()` context includes an `organizers` queryset filtered to
  the requested tournament only.
- Template rendering: a tournament with co-organizers (and no
  `main_organizer`) renders their cards; a tournament with both renders both;
  a tournament with neither still renders the existing empty state.
- Permission regression: a user who is only a co-organizer (not
  `main_organizer`, not superuser) does **not** pass
  `is_user_has_admin_access_to_tournament` — confirms the "view/credit only"
  decision stays enforced.

### 6. Translations

New user-facing strings `_("Organizer")` and `_("Role")` need entries in
`locale/uk/LC_MESSAGES/django.po` and `locale/en/LC_MESSAGES/django.po`,
followed by `compilemessages` to regenerate the `.mo` files (both committed
together, matching existing convention).

## Non-goals / explicitly out of scope

- No change to `main_organizer`, `organizer_club`, or `federation_delegat`.
- No change to who has tournament-admin rights.
- No self-service editing — admin-only, same as every other organizer/arbiter
  field today.
- No change to the `?output_format=json` tournament export.
- No change to `tournament_protocol.html`.
