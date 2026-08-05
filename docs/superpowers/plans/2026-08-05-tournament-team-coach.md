# Per-Tournament Team Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an optional coach (any `Player`) be assigned to a team's registration for one specific tournament — settable at self-service registration, editable in Django admin, visible on the tournament page, and included in the tournament JSON export.

**Architecture:** Add a nullable `coach` FK to `TeamTournamentMembership` (the existing per-tournament team-registration row), then thread it through the registration form/view, the admin inline, the tournament page template, and the JSON export — following the exact patterns already used for `ArbiterTournamentMembership.arbiter` and `team.team.get_display_capitan`.

**Tech Stack:** Django 5, PostgreSQL 17, server-rendered templates (Bootstrap 5 + jQuery + DataTables + select2), Django admin, `manage.py test`.

**Spec:** [`docs/superpowers/specs/2026-08-05-tournament-team-coach-design.md`](../specs/2026-08-05-tournament-team-coach-design.md)

## Global Constraints

- Any command below runs inside the running local stack container:
  `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py <command>` (per `CLAUDE.md`). Start the stack first with `./deploy/local_run.sh` if it isn't already running.
- Never edit an existing migration file — always generate a new one with `makemigrations`.
- User-visible strings use `_()` / `{% trans %}` (Ukrainian locale is primary); translations live in `locale/uk/LC_MESSAGES/django.po` and `locale/en/LC_MESSAGES/django.po`, each with a compiled `.mo` committed alongside it.
- A coach may be any `Player`, with no overlap/uniqueness restriction against the team roster or other teams in the tournament (confirmed with stakeholder — see spec §Requirements).
- Coach is available on every tournament format, including single-player ("individual") tournaments — no `is_single_player_format` gating anywhere in this feature.
- Commit after each task with a conventional commit message (`type(scope): description`).

---

### Task 1: `coach` field on `TeamTournamentMembership`

**Files:**
- Modify: `components/web-api/application/federation/models/tournament.py:524-534`
- Test: `components/web-api/application/federation/tests.py`
- Migration: generated, `components/web-api/application/federation/migrations/` (next after `0076_club_is_active.py`)

**Interfaces:**
- Produces: `TeamTournamentMembership.coach` — nullable `ForeignKey(Player, on_delete=SET_NULL, related_name='coached_team_memberships')`. Every later task reads/writes this attribute.

- [ ] **Step 1: Write the failing test**

Add to `federation/tests.py`, near the other tournament-model tests (e.g. after `TeamCaptainSelectionTests`, around line 435):

```python
class TeamTournamentMembershipCoachFieldTests(TestCase):
    def create_player(self, username):
        return Player.objects.create(
            user=User.objects.create_user(username=username),
            name=username.title(),
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
        )

    def create_tournament(self):
        return Tournament.objects.create(
            name='Coach Field Cup',
            category='open',
            place='Kyiv',
            start_date=date(2026, 6, 1),
            format='swiko',
        )

    def test_coach_defaults_to_none_and_can_be_set(self):
        coach = self.create_player('coach-field-coach')
        tournament = self.create_tournament()
        team = Team.objects.create(name='Coach Field Team')

        membership = TeamTournamentMembership.objects.create(tournament=tournament, team=team)
        self.assertIsNone(membership.coach)

        membership.coach = coach
        membership.save()
        membership.refresh_from_db()
        self.assertEqual(membership.coach, coach)

    def test_deleting_coach_player_clears_membership_instead_of_deleting_it(self):
        coach = self.create_player('coach-field-deleted-coach')
        tournament = self.create_tournament()
        team = Team.objects.create(name='Coach Field Team Two')
        membership = TeamTournamentMembership.objects.create(tournament=tournament, team=team, coach=coach)

        coach.delete()

        membership.refresh_from_db()
        self.assertIsNone(membership.coach)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TeamTournamentMembershipCoachFieldTests -v 2`
Expected: FAIL — `TypeError: 'coach' is an invalid keyword argument for this function` (or `AttributeError` on `membership.coach`), since the field does not exist yet.

- [ ] **Step 3: Add the field**

In `federation/models/tournament.py`, modify the `TeamTournamentMembership` class (currently lines 524-534):

```python
# Teams to Tournaments relation
class TeamTournamentMembership(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, verbose_name="Турнір", null=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, verbose_name="Команда", null=True)
    coach = models.ForeignKey(
        Player, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Coach'), related_name='coached_team_memberships',
    )
    place_min = models.IntegerField(_('Place'), default=0)
    place_max = models.IntegerField(_('Place (maximum)'), default=0)
    date_registration = models.DateField(_('Registration date'), default=timezone.now)
```

(`Player` is already imported at the top of this file — `from federation.models.player import Player` — and `ArbiterTournamentMembership.arbiter` right below uses the same direct-class-reference style, so this matches the closest sibling model.)

- [ ] **Step 4: Generate and apply the migration**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py makemigrations federation`
Expected: `Migrations for 'federation': federation/migrations/0077_teamtournamentmembership_coach.py - Add field coach to teamtournamentmembership` (exact filename/number may differ slightly — use whatever Django generates, do not hand-author it).

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py migrate`
Expected: `Applying federation.0077_teamtournamentmembership_coach... OK` (or the actual generated number).

- [ ] **Step 5: Run test to verify it passes**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TeamTournamentMembershipCoachFieldTests -v 2`
Expected: `OK` (2 tests)

- [ ] **Step 6: Run full test suite to check for regressions**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py check && docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation`
Expected: `OK` — no regressions (this field is additive/nullable, so nothing else should reference it yet).

- [ ] **Step 7: Commit**

```bash
git add components/web-api/application/federation/models/tournament.py \
        components/web-api/application/federation/migrations/ \
        components/web-api/application/federation/tests.py
git commit -m "feat(tournament): add optional coach field to team-tournament membership"
```

---

### Task 2: `coach` field on `RegistrationTeamForm`

**Files:**
- Modify: `components/web-api/application/federation/forms/registration_team_form.py`
- Test: `components/web-api/application/federation/tests.py`

**Interfaces:**
- Consumes: nothing new from Task 1 directly (form-only validation logic; no DB writes here).
- Produces: `RegistrationTeamForm.fields['coach']` (optional `CharField` backed by a `Select` widget, class `player-autocomplete`); `RegistrationTeamForm.verified_coach_id: Optional[int]`, populated by `is_valid()` exactly like `verified_player_ids` is today. Task 3 reads `verified_coach_id`.

- [ ] **Step 1: Write the failing test**

Add to `federation/tests.py`, right after `TeamRegistrationRedesignTests` (after its last test, `test_team_registration_form_keeps_capitan_first_team_creation_order`, around line 1794):

```python
class TeamRegistrationFormCoachTests(TestCase):
    def create_tournament(self):
        return Tournament.objects.create(
            name='Coach Form Cup',
            category='open',
            place='Kyiv',
            start_date=date(2026, 6, 1),
            number_of_players_in_team_min=2,
            number_of_players_in_team_max=2,
            format='swiko',
        )

    def create_player(self, username):
        return Player.objects.create(
            user=User.objects.create_user(username=username),
            name=username.title(),
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
        )

    def test_coach_field_is_optional(self):
        tournament = self.create_tournament()
        first = self.create_player('coach-form-first')
        second = self.create_player('coach-form-second')

        form = RegistrationTeamForm(
            data={'players[1]': str(first.pk), 'players[2]': str(second.pk)},
            tournament=tournament,
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())
        self.assertIsNone(form.verified_coach_id)

    def test_coach_field_resolves_to_verified_coach_id(self):
        tournament = self.create_tournament()
        first = self.create_player('coach-form-third')
        second = self.create_player('coach-form-fourth')
        coach = self.create_player('coach-form-coach')

        form = RegistrationTeamForm(
            data={'players[1]': str(first.pk), 'players[2]': str(second.pk), 'coach': str(coach.pk)},
            tournament=tournament,
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())
        self.assertEqual(form.verified_coach_id, coach.pk)

    def test_coach_can_overlap_with_roster_or_other_teams(self):
        tournament = self.create_tournament()
        first = self.create_player('coach-form-fifth')
        second = self.create_player('coach-form-sixth')
        # `first` is both a roster player and the selected coach: no overlap check applies.
        form = RegistrationTeamForm(
            data={'players[1]': str(first.pk), 'players[2]': str(second.pk), 'coach': str(first.pk)},
            tournament=tournament,
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())
        self.assertEqual(form.verified_coach_id, first.pk)

    def test_coach_field_rejects_nonexistent_player_id(self):
        tournament = self.create_tournament()
        first = self.create_player('coach-form-seventh')
        second = self.create_player('coach-form-eighth')

        form = RegistrationTeamForm(
            data={'players[1]': str(first.pk), 'players[2]': str(second.pk), 'coach': '999999'},
            tournament=tournament,
        )

        self.assertFalse(form.is_valid())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TeamRegistrationFormCoachTests -v 2`
Expected: FAIL — `AttributeError: 'RegistrationTeamForm' object has no attribute 'verified_coach_id'` (and the field itself doesn't exist yet, so posting `'coach'` data has no effect).

- [ ] **Step 3: Add the field and validation**

In `federation/forms/registration_team_form.py`:

1. Initialize `verified_coach_id` alongside `verified_player_ids` in `__init__` (currently line 16):

```python
    def __init__(self, *args, **kwargs):
        self.tournament = kwargs.pop('tournament')
        self.verified_player_ids = []
        self.verified_coach_id = None
```

2. After the existing player-fields loop and before `self.helper = FormHelper()` (currently line 55), add the coach field:

```python
        self.fields['coach'] = forms.CharField(
            widget=forms.Select(
                attrs={
                    'class': 'player-autocomplete',
                    'data-minimum-input-length': PLAYER_SEARCH_MINIMUM_INPUT_LENGTH,
                    'data-placeholder': _("Search coach by first or last name"),
                },
            ),
            label=_("Coach"),
            required=False,
        )
        selected_coach_id = None
        if self.is_bound:
            selected_coach_id = self.data.get('coach')
        elif self.initial.get('coach'):
            selected_coach_id = self.initial.get('coach')

        if selected_coach_id:
            try:
                selected_coach = Player.objects.get(pk=selected_coach_id)
                self.fields['coach'].widget.choices = [(selected_coach.pk, selected_coach.get_name())]
            except Player.DoesNotExist:
                self.fields['coach'].widget.choices = [(selected_coach_id, selected_coach_id)]

        self.helper = FormHelper()
```

3. In `is_valid()`, replace the final `return True` (currently line 116) with:

```python
        self.verified_coach_id = None
        coach_id = self.cleaned_data.get('coach')
        if coach_id:
            try:
                coach = Player.objects.get(pk=coach_id)
            except Player.DoesNotExist:
                self.add_error(None, _('Coach with number %(coach_id)s does not exist') % {'coach_id': coach_id})
                return False
            self.verified_coach_id = coach.pk

        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TeamRegistrationFormCoachTests -v 2`
Expected: `OK` (4 tests)

- [ ] **Step 5: Run the existing registration form/view tests to check for regressions**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TeamRegistrationRedesignTests federation.tests.TournamentRegistrationLifecycleTests -v 2`
Expected: `OK` — unaffected, since `coach` is optional and none of these tests post it.

- [ ] **Step 6: Commit**

```bash
git add components/web-api/application/federation/forms/registration_team_form.py \
        components/web-api/application/federation/tests.py
git commit -m "feat(registration): add optional coach field to team registration form"
```

---

### Task 3: Wire coach through `register_team` view and template

**Files:**
- Modify: `components/web-api/application/federation/models/tournament.py` (`Tournament.add_team`, currently lines 109-111)
- Modify: `components/web-api/application/federation/views/register.py` (`register_team`, currently lines 39-73)
- Modify: `components/web-api/application/federation/templates/register/team.html`
- Test: `components/web-api/application/federation/tests.py`

**Interfaces:**
- Consumes: Task 1's `TeamTournamentMembership.coach`; Task 2's `RegistrationTeamForm.verified_coach_id`.
- Produces: `Tournament.add_team(self, team, coach_id=None)` — the only existing caller (`register.py:59`) is updated in this task; no other callers exist in the codebase. (Originally specified as `coach=None` taking a `Player` instance; revised during Task 3's review to take a raw `coach_id` instead, since a caller with an already-validated id doesn't need to re-fetch the `Player` row just to hand it back to the ORM — see Step 3/4 below.)

- [ ] **Step 1: Write the failing test**

Add to `federation/tests.py`, right after the `TeamRegistrationFormCoachTests` class added in Task 2:

```python
class TeamRegistrationCoachPersistenceTests(TestCase):
    def create_tournament(self):
        return Tournament.objects.create(
            name='Coach Persistence Cup',
            category='open',
            place='Kyiv',
            start_date=(timezone.now() + timedelta(days=30)).date(),
            date_registration_stop=timezone.now() + timedelta(days=29),
            number_of_players_in_team_min=2,
            number_of_players_in_team_max=2,
            teams_limit=100,
            format='swiko',
        )

    def create_player(self, username):
        return Player.objects.create(
            user=User.objects.create_user(username=username),
            name=username.title(),
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
        )

    def test_register_team_persists_selected_coach(self):
        tournament = self.create_tournament()
        first = self.create_player('coach-persist-first')
        second = self.create_player('coach-persist-second')
        coach = self.create_player('coach-persist-coach')

        response = self.client.post(f'/register/team/{tournament.pk}/', {
            'players[1]': str(first.pk),
            'players[2]': str(second.pk),
            'coach': str(coach.pk),
        })

        self.assertEqual(response.status_code, 302)
        membership = TeamTournamentMembership.objects.get(tournament=tournament)
        self.assertEqual(membership.coach, coach)

    def test_register_team_without_coach_leaves_it_blank(self):
        tournament = self.create_tournament()
        first = self.create_player('coach-persist-third')
        second = self.create_player('coach-persist-fourth')

        response = self.client.post(f'/register/team/{tournament.pk}/', {
            'players[1]': str(first.pk),
            'players[2]': str(second.pk),
        })

        self.assertEqual(response.status_code, 302)
        membership = TeamTournamentMembership.objects.get(tournament=tournament)
        self.assertIsNone(membership.coach)

    def test_team_registration_page_renders_coach_field(self):
        tournament = self.create_tournament()

        response = self.client.get(f'/register/team/{tournament.pk}')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="coach"')
        self.assertContains(response, 'Search coach by first or last name')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TeamRegistrationCoachPersistenceTests -v 2`
Expected: FAIL — the first two tests fail because `add_team` doesn't accept `coach`/nothing sets it (membership.coach stays `None` even when posted, or `TypeError` once `register_team` is updated to pass `coach=` before `add_team` accepts it); the third fails because `name="coach"` isn't rendered yet.

- [ ] **Step 3: Update `Tournament.add_team`**

In `federation/models/tournament.py`, modify (currently lines 109-111):

```python
    '''
        add team to current tournament
    '''
    def add_team(self, team, coach_id=None):
        new_team = TeamTournamentMembership(tournament=self, team=team, coach_id=coach_id)
        new_team.save()
```

(Takes a raw `coach_id`, not a `Player` instance — the caller already has a validated id via `verified_coach_id` and Django's FK `<field>_id` kwarg accepts it directly, with no extra DB fetch needed. See the note below Step 4.)

- [ ] **Step 4: Update `register_team`**

In `federation/views/register.py`, modify the success branch (currently lines 56-62):

```python
        elif team_registration_form.is_valid():
            player_ids = list(reversed(team_registration_form.verified_player_ids))
            team = Team.get_or_create_for_players(player_ids=player_ids)
            tournament.add_team(team, coach_id=team_registration_form.verified_coach_id)
            tournament.recalculate_power_on_registration()
            messages.success(request, _('Team registered.'), extra_tags='success')
            return redirect('tournament', id=tournament.pk)
```

**Note (revised during Task 3's review):** the original version of this step re-fetched the coach via `Player.objects.get(pk=team_registration_form.verified_coach_id)` before passing it to `add_team`. That re-fetch was an unhandled, redundant DB read of a row the form had already validated moments earlier — in the (narrow, low-probability) window where that exact `Player` was deleted between the form's check and this fetch, it would raise an uncaught `Player.DoesNotExist` and crash the request with a 500. Passing `coach_id` straight through removes the redundant fetch entirely, so there's nothing left to race: `TeamTournamentMembership.coach` is a nullable `ForeignKey(Player, on_delete=SET_NULL)`, so a stale id would fail at the DB FK-constraint level (an essentially-impossible case, since the form validated it a moment before) rather than as an unhandled Python exception on an ordinary request path.

- [ ] **Step 5: Render the coach field in the template**

In `federation/templates/register/team.html`, insert a new field block after the closing `</div>` of `registration-field-grid` (currently line 65) and before the `registration-actions` div (currently line 67):

```html
                        <div class="registration-field-grid registration-team-coach-grid">
                            <div class="registration-field registration-team-field">
                                <label for="{{ team_registration_form.coach.id_for_label }}">{{ team_registration_form.coach.label }}</label>
                                {{ team_registration_form.coach }}
                                {% if team_registration_form.coach.errors %}
                                    <div class="registration-field-errors">{{ team_registration_form.coach.errors }}</div>
                                {% endif %}
                            </div>
                        </div>
```

No JS changes needed: the coach widget already carries `class="player-autocomplete"` (set in Task 2), and the existing `$('.player-autocomplete').each(...)` select2 initializer in this same template (lines 131-167) already applies to every element with that class.

- [ ] **Step 6: Run test to verify it passes**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TeamRegistrationCoachPersistenceTests -v 2`
Expected: `OK` (3 tests)

- [ ] **Step 7: Run the broader registration test suite to check for regressions**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TeamRegistrationRedesignTests federation.tests.TournamentRegistrationLifecycleTests federation.tests.TeamRegistrationFormCoachTests -v 2`
Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add components/web-api/application/federation/models/tournament.py \
        components/web-api/application/federation/views/register.py \
        components/web-api/application/federation/templates/register/team.html \
        components/web-api/application/federation/tests.py
git commit -m "feat(registration): let a team register with an optional coach"
```

---

### Task 4: Expose `coach` on the `TeamsTournamentMembershipInline` admin

**Files:**
- Modify: `components/web-api/application/federation/models/tournament.py` (`TeamsTournamentMembershipInline`, currently lines 609-616)
- Modify: `components/web-api/application/federation/tests.py` (import block)
- Test: `components/web-api/application/federation/tests.py`

**Interfaces:**
- Consumes: Task 1's `TeamTournamentMembership.coach`.
- Produces: nothing new consumed by later tasks (leaf feature — admin editing only).

**Note on scope:** the spec's testing section called for a test proving a saved `coach` value round-trips through the inline (set, then cleared). No test in this codebase currently POSTs a full `TeamsTournamentMembershipInline` formset — doing so requires supplying every non-`blank=True` field on the parent `Tournament` ModelForm (name, category, place, format, start_date, start_time, and more), which no existing test constructs, and getting that payload subtly wrong would produce a flaky/misleading test rather than real coverage. This task instead verifies the field is wired into the inline (`autocomplete_fields`) and actually renders for an existing row — the same depth of admin-inline coverage every other field on this inline (`team`, `place_min`, `place_max`) already has today. The actual save-and-persist behavior for an inline FK field is Django admin machinery, already exercised by Django's own test suite; re-proving it here would test the framework, not this feature.

- [ ] **Step 1: Write the failing test**

Add `TeamsTournamentMembershipInline` to the existing import from `federation.models.tournament` in `federation/tests.py` (currently lines 39-43):

```python
from federation.models.tournament import (
    ArbiterTeamTournamentAdminInline,
    TeamsTournamentMembershipInline,
    TeamTournamentMembership,
    Tournament,
)
```

Then add a new test class after `RestrictedRelatedWidgetAdminMixinTests` (after line 1104):

```python
class TeamTournamentMembershipCoachAdminTests(TestCase):
    def create_admin(self):
        return User.objects.create_superuser(
            username='team-coach-admin',
            email='team-coach-admin@example.com',
            password='AdminPass123!',
        )

    def test_coach_is_an_autocomplete_field_on_the_inline(self):
        self.assertIn('coach', TeamsTournamentMembershipInline.autocomplete_fields)

    def test_tournament_change_page_renders_coach_autocomplete_for_existing_team(self):
        tournament = Tournament.objects.create(
            name='Admin Coach Cup',
            category='open',
            place='Kyiv',
            start_date=date(2026, 6, 1),
            format='swiko',
        )
        team = Team.objects.create(name='Admin Coach Team')
        tournament.add_team(team)
        self.client.force_login(self.create_admin())

        response = self.client.get('/admin/federation/tournament/{}/change/'.format(tournament.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_teamtournamentmembership_set-0-coach"')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TeamTournamentMembershipCoachAdminTests -v 2`
Expected: FAIL — `'coach' not in ['team']` for the first test; the second fails because the rendered page has no element with that id.

- [ ] **Step 3: Add `coach` to the inline**

In `federation/models/tournament.py`, modify `TeamsTournamentMembershipInline` (currently lines 609-616):

```python
# Classes for admin
class TeamsTournamentMembershipInline(RestrictedRelatedWidgetAdminMixin, admin.TabularInline):
    model = TeamTournamentMembership
    extra = 0
    autocomplete_fields = ['team', 'coach']

    class Meta:
        verbose_name = 'Команди турніру'
        verbose_name_plural = 'Команди турніру'
```

`RestrictedRelatedWidgetAdminMixin` already strips the add/delete icons from every related-object widget generically, so no further change is needed there.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TeamTournamentMembershipCoachAdminTests -v 2`
Expected: `OK` (2 tests)

- [ ] **Step 5: Run the admin regression tests**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.RestrictedRelatedWidgetAdminMixinTests federation.tests.TournamentPowerAdminActionTests -v 2`
Expected: `OK` — `save_formset`'s power-recalculation-on-change behavior (`ArbiterTeamTournamentAdminInline.save_formset`) is untouched by this task; `coach` isn't part of `recalculate_power_for_current_state()`.

- [ ] **Step 6: Commit**

```bash
git add components/web-api/application/federation/models/tournament.py \
        components/web-api/application/federation/tests.py
git commit -m "feat(admin): make coach editable on the team-tournament membership inline"
```

---

### Task 5: Show coach on the tournament page

**Files:**
- Modify: `components/web-api/application/federation/views/tournaments.py:997`
- Modify: `components/web-api/application/federation/templates/tournaments/tournament_teams.html`
- Modify: `components/web-api/application/static/style-v2.css`
- Test: `components/web-api/application/federation/tests.py`

**Interfaces:**
- Consumes: Task 1's `TeamTournamentMembership.coach`; the `teams` context variable already produced by the `tournament()` view (a `TeamTournamentMembership` queryset).
- Produces: nothing consumed by later tasks (leaf feature — display only). CSS classes introduced: `tournament-team-coach-col`, `tournament-team-coach-cell` (reuses the existing `tournament-team-captain-name` and `tournament-team-muted` classes for content styling — no new name-link CSS needed).

**Note on scope:** this table is DataTables-driven with a `columns: [...]` JS config that must positionally match the rendered `<th>`s, and it has a large amount of pre-existing pixel-tuned responsive CSS across several breakpoints (roughly `static/style-v2.css:10080-10650`) fine-tuning the *existing* columns for a mid-size tablet range. This task adds correct base styling (a fixed-width `<col>`, matching the pattern used for `tournament-team-club-col`) and relies on the table wrapper's existing `overflow-x: auto` (`static/style-v2.css:9418-9421`) as the safety net if the extra column doesn't fit at that tablet breakpoint — it does not hand-tune every breakpoint-specific override for the new column. The truly narrow-viewport experience (`≤991.98px`) is entirely unaffected, since below that width the table itself is hidden in favor of the separate mobile-card markup this task also updates.

- [ ] **Step 1: Write the failing test**

Add to `federation/tests.py`, after the `TournamentTeamExportJsonTests` class (after line 1554, before `OptionalRegistrationEmailTests`):

```python
class TournamentPageCoachDisplayTests(TestCase):
    def create_player(self, username):
        return Player.objects.create(
            user=User.objects.create_user(username=username),
            name=username.title(),
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
        )

    def create_tournament(self):
        return Tournament.objects.create(
            name='Coach Display Cup',
            category='open',
            place='Kyiv',
            start_date=date(2026, 6, 1),
            number_of_players_in_team_min=2,
            number_of_players_in_team_max=2,
            format='swiko',
        )

    def create_team(self, name, players):
        team = Team.objects.create(name=name)
        for index, player in enumerate(players):
            PlayerTeamMembership.objects.create(team=team, player=player, is_capitan=index == 0)
        return team

    def test_tournament_page_shows_coach_name_and_link(self):
        coach = self.create_player('display-coach')
        first = self.create_player('display-player-one')
        second = self.create_player('display-player-two')
        tournament = self.create_tournament()
        team = self.create_team('Coached Pair', [first, second])
        tournament.add_team(team, coach_id=coach.pk)

        response = self.client.get('/tournament/{}'.format(tournament.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tournament-team-coach-cell')
        self.assertContains(response, coach.get_name())
        self.assertContains(response, '/player/{}'.format(coach.pk))

    def test_tournament_page_shows_dash_when_no_coach_assigned(self):
        first = self.create_player('nocoach-player-one')
        second = self.create_player('nocoach-player-two')
        tournament = self.create_tournament()
        team = self.create_team('Uncoached Pair', [first, second])
        tournament.add_team(team)

        response = self.client.get('/tournament/{}'.format(tournament.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tournament-team-coach-cell')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TournamentPageCoachDisplayTests -v 2`
Expected: FAIL — `tournament-team-coach-cell` is not in the response yet.

- [ ] **Step 3: Add `coach` to the view's `select_related`**

In `federation/views/tournaments.py`, modify the `teams` queryset inside `tournament()` (currently line 997):

```python
        .select_related('team', 'tournament', 'tournament__main_organizer', 'tournament__main_organizer__user', 'coach')
```

- [ ] **Step 4: Add the desktop table column**

In `federation/templates/tournaments/tournament_teams.html`:

1. Colgroup — insert right after `<col class="tournament-team-name-col">` (currently line 23):

```html
                <col class="tournament-team-coach-col">
```

2. Header row — insert right after the closing `</th>` of the Captain/Participant header (currently lines 40-46):

```html
                    <th class="tournament-team-coach-col">{% trans "Coach" %}</th>
```

3. Body cell — insert right after the closing `</td>` of the name/captain cell (currently ends line 134, right before the `{% if tournament_detail.is_single_player_format %}` club-cell block that starts at line 135):

```html
                    <td class="tournament-team-coach-cell" data-label="{% trans "Coach" %}">
                        {% if team.coach %}
                            <a class="tournament-team-captain-name" href="{% url 'player' id=team.coach.pk %}">{{ team.coach.get_name }}</a>
                        {% else %}
                            <span class="tournament-team-muted">&mdash;</span>
                        {% endif %}
                    </td>
```

- [ ] **Step 5: Add the mobile card section**

In the same file, insert a new unconditional section right after the closing `</section>` of the Captain/Participant mobile section (currently ends line 306) and before the `{% if not tournament_detail.is_single_player_format %}` Athletes section that starts at line 308:

```html
                <section class="tournament-team-mobile-people">
                    <h3>{% trans "Coach" %}</h3>
                    {% if team.coach %}
                        <a class="tournament-team-captain-name" href="{% url 'player' id=team.coach.pk %}">{{ team.coach.get_name }}</a>
                    {% else %}
                        <span class="tournament-team-muted">&mdash;</span>
                    {% endif %}
                </section>
```

- [ ] **Step 6: Fix the DataTables `columns` config to match the new column count**

In the same file's `<script>` block, the `columns: [...]` array (currently lines 501-522) has two branches that must each gain one entry for the new, always-present Coach column, positioned right after the place/captain entries (index 2) and before the athletes/club entry:

Single-player-format branch (currently lines 502-511) — change:

```js
                { searchable: true, orderable: true, type: "num" },
                { searchable: true, orderable: true },
                { searchable: true, orderable: true },
```

to:

```js
                { searchable: true, orderable: true, type: "num" },
                { searchable: true, orderable: true },
                { searchable: true, orderable: false },
                { searchable: true, orderable: true },
```

Team-format branch (currently lines 513-515) — change:

```js
                { searchable: true, orderable: true, type: "num" },
                { searchable: true, orderable: true },
                { searchable: true, orderable: false },
```

to:

```js
                { searchable: true, orderable: true, type: "num" },
                { searchable: true, orderable: true },
                { searchable: true, orderable: false },
                { searchable: true, orderable: false },
```

(the rest of each branch — the optional score entry, power, date, actions — is unchanged; it just now sits one position further along).

- [ ] **Step 7: Update `powerColumnIndex`**

In the same `<script>` block, modify (currently line 421):

```js
    var powerColumnIndex = {% if tournament.is_processing_finished or tournament.is_goes_to_rating %}5{% else %}4{% endif %};
```

(each branch's value increases by 1, since the new Coach column always sits before the power column now).

- [ ] **Step 8: Add base CSS for the new column**

In `static/style-v2.css`, insert right after the `.tournament-team-name-col { width: 12rem; }` rule (currently lines 9606-9608):

```css
.tournament-team-coach-col {
  width: 10rem;
}
```

- [ ] **Step 9: Run test to verify it passes**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TournamentPageCoachDisplayTests -v 2`
Expected: `OK` (2 tests)

- [ ] **Step 10: Manually verify in the browser**

Start the stack if it isn't running (`./deploy/local_run.sh`), open `http://localhost:60102/tournament/<id>` for a tournament with at least one registered team, and confirm:
- The "Coach" column appears in the desktop table between "Captain"/"Participant" and "Athletes"/"Club", showing "—" for teams with no coach.
- The mobile card view (resize the browser below ~991px width) shows a "Coach" section per team.
- Sorting by clicking other column headers (e.g. "Team power") still sorts on the correct column (this exercises `powerColumnIndex` and the `columns` array alignment).

- [ ] **Step 11: Run the broader tournament-page test suite to check for regressions**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TournamentListingPageTests federation.tests.PlayerTournamentListTests -v 2`
Expected: `OK`

- [ ] **Step 12: Commit**

```bash
git add components/web-api/application/federation/views/tournaments.py \
        components/web-api/application/federation/templates/tournaments/tournament_teams.html \
        components/web-api/application/static/style-v2.css \
        components/web-api/application/federation/tests.py
git commit -m "feat(tournament): show team coach on the tournament page"
```

---

### Task 6: Include `coach` in the tournament JSON export

**Files:**
- Modify: `components/web-api/application/federation/views/tournaments.py` (`tournament_teams_export`, currently lines 1032-1214)
- Modify: `docs/api.md`
- Test: `components/web-api/application/federation/tests.py`

**Interfaces:**
- Consumes: Task 1's `TeamTournamentMembership.coach`; the existing `_player_brief()` helper (currently defined at `tournaments.py:1118`, already used for `main_organizer`/`federation_delegat`/`arbiters`).
- Produces: `coach` key on each team object in the `?format=json` response — `_player_brief(team.coach)` shape (`id`, `name`, `surname`, `second_name`, `avatar_url`) or `null`. `docs/api.md` documents this for external consumers (the draw tool).

- [ ] **Step 1: Write the failing test**

Extend `TournamentTeamExportJsonTests` in `federation/tests.py`. First, give `create_team_membership` (currently lines 1442-1452) an optional `coach` parameter:

```python
    def create_team_membership(self, tournament, players, name, place_min, power='0.0000', coach=None):
        team = Team.objects.create(name=name)
        for index, player in enumerate(players):
            PlayerTeamMembership.objects.create(team=team, player=player, is_capitan=index == 0)

        return TeamTournamentMembership.objects.create(
            tournament=tournament,
            team=team,
            place_min=place_min,
            power=Decimal(power),
            coach=coach,
        )
```

Then add two new test methods after `test_json_export_marks_insurance_valid_when_not_required` (after line 1553):

```python
    def test_json_export_includes_coach_when_assigned(self):
        coach = self.create_player('export-coach')
        first = self.create_player('coach-team-first')
        second = self.create_player('coach-team-second')
        tournament = self.create_tournament()
        self.create_team_membership(tournament, [first, second], 'Coached Pair', place_min=1, coach=coach)

        response = self.client.get('/tournament/team_export/{}'.format(tournament.pk), {'format': 'json'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['teams'][0]['coach']['id'], coach.pk)
        self.assertEqual(data['teams'][0]['coach']['name'], coach.name)
        self.assertEqual(data['teams'][0]['coach']['surname'], coach.surname)

    def test_json_export_coach_is_null_when_not_assigned(self):
        first = self.create_player('nocoach-team-first')
        second = self.create_player('nocoach-team-second')
        tournament = self.create_tournament()
        self.create_team_membership(tournament, [first, second], 'Uncoached Pair', place_min=1)

        response = self.client.get('/tournament/team_export/{}'.format(tournament.pk), {'format': 'json'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data['teams'][0]['coach'])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TournamentTeamExportJsonTests -v 2`
Expected: FAIL — `KeyError: 'coach'` on the first new test; the second passes accidentally only if you check `.get('coach')`, but as written (`data['teams'][0]['coach']`) it also fails with `KeyError`.

- [ ] **Step 3: Add `coach` to the export**

In `federation/views/tournaments.py`:

1. Extend the queryset's `select_related` (currently line 1043):

```python
        .select_related('team', 'coach')
```

2. Add `coach` to the per-team dict (currently lines 1159-1172, inside the `elif output_format == 'json':` branch) — insert right after `'rating_power': team.rating_power,`:

```python
            current_team = {
                'id': team.team.pk,
                'power': team_power,
                'team_power': team_power,
                'place_min': team.place_min,
                'place_max': team.place_max,
                'date_registration': team.date_registration,
                'rating_points': team.rating_points,
                'rating_power': team.rating_power,
                'coach': _player_brief(team.coach) if team.coach else None,
                'name': team.team.get_short_name(),
                'club': _club_export(team_club, request) if team_club else None,
                'club_logo_url': _media_file_url(request, team_club.logo) if team_club else None,
                'players': []
            }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TournamentTeamExportJsonTests -v 2`
Expected: `OK` (5 tests)

- [ ] **Step 5: Document the new field**

In `docs/api.md`, in the JSON response example under `GET /tournament/team_export/<id>?format=json` (currently lines 118-150), add `"coach"` right after `"date_registration"`:

```json
      "date_registration": "2024-05-01T12:00:00Z",
      "coach": { "id": 55, "name": "Ivan", "surname": "Petrenko", "second_name": "", "avatar_url": null },
      "rating_points": 120,
```

And extend the note right below the example (currently line 154):

```markdown
`teams[].club` and `teams[].club_logo_url` are populated only when every player in the exported team has the same current club; otherwise both values are `null`. `teams[].coach` uses the same brief-player shape as `tournament.arbiters[]` entries (minus `is_main_arbiter`), or `null` when no coach is assigned. `players[].rating` uses the tournament-specific rating field: regular, B, League, or inclusive.
```

- [ ] **Step 6: Commit**

```bash
git add components/web-api/application/federation/views/tournaments.py \
        components/web-api/application/federation/tests.py \
        docs/api.md
git commit -m "feat(api): include team coach in the tournament JSON export"
```

---

### Task 7: Translations

**Files:**
- Modify: `components/web-api/application/locale/uk/LC_MESSAGES/django.po` and `.mo`
- Modify: `components/web-api/application/locale/en/LC_MESSAGES/django.po` and `.mo`

**Interfaces:**
- Consumes: every `_()` / `{% trans %}` string introduced in Tasks 2-6 (`"Coach"`, `"Search coach by first or last name"`). No new interfaces produced — this is the final task.

**Note:** `_("Coach")` reuses an msgid that already exists in both locale files (from `federation/models/national_teams.py:34`, translated as "Тренер" in Ukrainian) — Django's `makemessages` will merge it automatically, adding new `#:` source references without touching the existing translation. Only `"Search coach by first or last name"` is a genuinely new string.

- [ ] **Step 1: Regenerate the `.po` files**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py makemessages -l uk -l en`
Expected: `processing locale uk` / `processing locale en`, and `git diff` on both `django.po` files shows: (a) new `#:` comment lines added to the existing `msgid "Coach"` entry pointing at the new source locations (`federation/models/tournament.py`, `federation/forms/registration_team_form.py`, `federation/templates/tournaments/tournament_teams.html`), and (b) one new empty-`msgstr` block for `msgid "Search coach by first or last name"`.

- [ ] **Step 2: Fill in the new translation**

In `locale/uk/LC_MESSAGES/django.po`, find the new entry and set:

```po
msgid "Search coach by first or last name"
msgstr "Пошук тренера за ім'ям або прізвищем"
```

In `locale/en/LC_MESSAGES/django.po`, find the new entry and set:

```po
msgid "Search coach by first or last name"
msgstr "Search coach by first or last name"
```

- [ ] **Step 3: Compile messages**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py compilemessages`
Expected: `processing file django.po in .../locale/uk/LC_MESSAGES` / `... locale/en/LC_MESSAGES`, regenerating both `.mo` files.

- [ ] **Step 4: Verify no `msgstr ""` was left on the new string**

Run: `grep -A1 'msgid "Search coach by first or last name"' components/web-api/application/locale/uk/LC_MESSAGES/django.po components/web-api/application/locale/en/LC_MESSAGES/django.po`
Expected: both show a non-empty `msgstr` line (as set in Step 2).

- [ ] **Step 5: Run the full test suite one last time**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py check && docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation`
Expected: `OK`, no failures anywhere in the app.

- [ ] **Step 6: Commit**

```bash
git add components/web-api/application/locale/uk/LC_MESSAGES/django.po \
        components/web-api/application/locale/uk/LC_MESSAGES/django.mo \
        components/web-api/application/locale/en/LC_MESSAGES/django.po \
        components/web-api/application/locale/en/LC_MESSAGES/django.mo
git commit -m "i18n(coach): translate the coach search placeholder string"
```

---

## After all tasks

Follow `superpowers:finishing-a-development-branch` to decide how to integrate `feat/tournament-team-coach` (the user's original request was a separate PR).
