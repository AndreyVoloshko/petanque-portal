# Multiple Tournament Organizers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a tournament have any number of co-organizers (`Player`s), in addition to the existing single `main_organizer`, each with a `role` that today only has one value but can grow more later without a schema change. Admin-managed, shown on the tournament delegations page.

**Architecture:** New through-table `OrganizerTournamentMembership` (`Tournament` FK + `Player` FK + `role` choices field), following the exact shape of the existing `ArbiterTournamentMembership`. Wired into the `Tournament` admin as a new inline, queried in the `tournament()` view, and rendered on `tournament_delegations.html` using the same person-card partial already used for `main_organizer` and arbiters.

**Tech Stack:** Django 5, PostgreSQL 17, server-rendered templates (Bootstrap 5), Django admin, `manage.py test`.

**Spec:** [`docs/superpowers/specs/2026-08-05-tournament-multiple-organizers-design.md`](../specs/2026-08-05-tournament-multiple-organizers-design.md)

## Global Constraints

- Any command below runs inside the running local stack container:
  `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py <command>` (per `CLAUDE.md`). Start the stack first with `./deploy/local_run.sh` if it isn't already running.
- Never edit an existing migration file — always generate a new one with `makemigrations`.
- `main_organizer`, `organizer_club`, and `federation_delegat` on `Tournament` are untouched — co-organizers are purely additive.
- Co-organizers do **not** get tournament-admin rights. `Tournament.is_user_has_admin_access_to_tournament` and `TeamTournamentMembership.is_user_has_admin_access_to_team` keep checking only `main_organizer` and `is_superuser` — confirmed with stakeholder, see spec §Requirements.
- Co-organizers are Django-admin-only editable — no self-service form, matching how `main_organizer`/`federation_delegat`/arbiters are managed today.
- `role` is a plain tuple `choices=` field (`ROLES = (('organizer', _('Organizer')),)`), not `models.TextChoices` — confirmed with stakeholder, matches every other choices field in this codebase.
- User-visible strings use `_()` / `{% trans %}`; translations live in `locale/uk/LC_MESSAGES/django.po` and `locale/en/LC_MESSAGES/django.po`, each with a compiled `.mo` committed alongside it.
- Commit after each task with a conventional commit message (`type(scope): description`).

---

### Task 1: `OrganizerTournamentMembership` model

**Files:**
- Modify: `components/web-api/application/federation/models/tournament.py:590-599` (insert after `ArbiterTournamentMembership`)
- Test: `components/web-api/application/federation/tests.py`
- Migration: generated, `components/web-api/application/federation/migrations/` (next after `0077_teamtournamentmembership_coach.py`)

**Interfaces:**
- Produces: `OrganizerTournamentMembership` — `tournament` (FK `Tournament`, `CASCADE`), `organizer` (FK `Player`, `CASCADE`), `role` (`CharField`, `choices=ROLES`, `default='organizer'`), `Meta.unique_together = ('tournament', 'organizer')`. Task 2 registers this in an admin inline; Task 3 queries it in the `tournament()` view. Both read/write `membership.organizer`, `membership.role`, `membership.tournament`.

- [ ] **Step 1: Write the failing test**

Add `IntegrityError`/`transaction` to the imports in `federation/tests.py` (currently line 20, next to the existing `django.db.models` import):

```python
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
```

Add `OrganizerTournamentMembership` to the existing import from `federation.models.tournament` (currently lines 40-45):

```python
from federation.models.tournament import (
    ArbiterTeamTournamentAdminInline,
    OrganizerTournamentMembership,
    TeamsTournamentMembershipInline,
    TeamTournamentMembership,
    Tournament,
)
```

Then add a new test class right after `TeamTournamentMembershipCoachFieldTests` (currently ends at line 478), before `class SeasonSnapshotGenerationTests(TestCase):` (currently line 481):

```python
class OrganizerTournamentMembershipTests(TestCase):
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
            name='Organizer Membership Cup',
            category='open',
            place='Kyiv',
            start_date=date(2026, 6, 1),
            format='swiko',
        )

    def test_role_defaults_to_organizer(self):
        tournament = self.create_tournament()
        organizer = self.create_player('membership-default-role')

        membership = OrganizerTournamentMembership.objects.create(tournament=tournament, organizer=organizer)

        self.assertEqual(membership.role, 'organizer')

    def test_duplicate_organizer_on_same_tournament_raises_integrity_error(self):
        tournament = self.create_tournament()
        organizer = self.create_player('membership-duplicate-organizer')
        OrganizerTournamentMembership.objects.create(tournament=tournament, organizer=organizer)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrganizerTournamentMembership.objects.create(tournament=tournament, organizer=organizer)

    def test_deleting_organizer_player_deletes_the_membership(self):
        tournament = self.create_tournament()
        organizer = self.create_player('membership-deleted-organizer')
        membership = OrganizerTournamentMembership.objects.create(tournament=tournament, organizer=organizer)

        organizer.delete()

        self.assertFalse(OrganizerTournamentMembership.objects.filter(pk=membership.pk).exists())

    def test_co_organizer_membership_does_not_grant_tournament_admin_access(self):
        tournament = self.create_tournament()
        co_organizer = self.create_player('membership-permission-check')
        OrganizerTournamentMembership.objects.create(tournament=tournament, organizer=co_organizer)

        self.assertFalse(tournament.is_user_has_admin_access_to_tournament(co_organizer.user))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.OrganizerTournamentMembershipTests -v 2`
Expected: FAIL — `ImportError: cannot import name 'OrganizerTournamentMembership' from 'federation.models.tournament'`, since the model doesn't exist yet.

- [ ] **Step 3: Add the model**

In `federation/models/tournament.py`, insert right after `ArbiterTournamentMembership`'s `Meta` block ends (currently lines 590-599), before the blank lines and `# Classes for admin` comment (currently line 601):

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

(`_` and `Player` are already imported at the top of this file, and `ArbiterTournamentMembership` right above uses the same direct-`CASCADE` style — this matches the closest sibling model.)

- [ ] **Step 4: Generate and apply the migration**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py makemigrations federation`
Expected: `Migrations for 'federation': federation/migrations/0078_organizertournamentmembership.py - Create model OrganizerTournamentMembership` (exact filename/number may differ slightly — use whatever Django generates, do not hand-author it).

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py migrate`
Expected: `Applying federation.0078_organizertournamentmembership... OK` (or the actual generated number).

- [ ] **Step 5: Run test to verify it passes**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.OrganizerTournamentMembershipTests -v 2`
Expected: `OK` (4 tests)

- [ ] **Step 6: Run full test suite to check for regressions**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py check && docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation`
Expected: `OK` — this is a new, unreferenced table, so nothing else should be affected.

- [ ] **Step 7: Commit**

```bash
git add components/web-api/application/federation/models/tournament.py \
        components/web-api/application/federation/migrations/ \
        components/web-api/application/federation/tests.py
git commit -m "feat(tournament): add OrganizerTournamentMembership model for co-organizers"
```

---

### Task 2: Admin inline for co-organizers

**Files:**
- Modify: `components/web-api/application/federation/models/tournament.py` (insert `OrganizerTournamentMembershipInline`; update `ArbiterTeamTournamentAdminInline.inlines`, currently line 624)
- Modify: `components/web-api/application/federation/tests.py` (import block)
- Test: `components/web-api/application/federation/tests.py`

**Interfaces:**
- Consumes: Task 1's `OrganizerTournamentMembership`.
- Produces: `OrganizerTournamentMembershipInline.autocomplete_fields = ['organizer']`, registered first in `ArbiterTeamTournamentAdminInline.inlines`. This is the only way co-organizers get assigned — no self-service form exists or is planned. Nothing later consumes this beyond the admin itself.

- [ ] **Step 1: Write the failing test**

Extend the `federation.models.tournament` import in `federation/tests.py` (as edited in Task 1) to also bring in `OrganizerTournamentMembershipInline`:

```python
from federation.models.tournament import (
    ArbiterTeamTournamentAdminInline,
    OrganizerTournamentMembership,
    OrganizerTournamentMembershipInline,
    TeamsTournamentMembershipInline,
    TeamTournamentMembership,
    Tournament,
)
```

Add a new test class right after `TeamTournamentMembershipCoachAdminTests` (currently ends at line 1262), before `class PlayerTournamentListTests(TestCase):` (currently line 1264):

```python
class OrganizerTournamentMembershipAdminTests(TestCase):
    def create_admin(self):
        return User.objects.create_superuser(
            username='organizer-membership-admin',
            email='organizer-membership-admin@example.com',
            password='AdminPass123!',
        )

    def create_tournament(self):
        return Tournament.objects.create(
            name='Admin Organizer Cup',
            category='open',
            place='Kyiv',
            start_date=date(2026, 6, 1),
            format='swiko',
        )

    def test_organizer_is_an_autocomplete_field_on_the_inline(self):
        self.assertIn('organizer', OrganizerTournamentMembershipInline.autocomplete_fields)

    def test_organizer_inline_is_registered_before_arbiter_and_team_inlines(self):
        self.assertEqual(ArbiterTeamTournamentAdminInline.inlines[0], OrganizerTournamentMembershipInline)

    def test_tournament_change_page_renders_organizer_autocomplete_for_existing_row(self):
        tournament = self.create_tournament()
        organizer = Player.objects.create(
            user=User.objects.create_user(username='admin-inline-co-organizer'),
            name='Admin-Inline',
            surname='Organizer',
            birth_date=date(1990, 1, 1),
            gender='M',
        )
        OrganizerTournamentMembership.objects.create(tournament=tournament, organizer=organizer)
        self.client.force_login(self.create_admin())

        response = self.client.get('/admin/federation/tournament/{}/change/'.format(tournament.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_organizertournamentmembership_set-0-organizer"')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.OrganizerTournamentMembershipAdminTests -v 2`
Expected: FAIL — `ImportError: cannot import name 'OrganizerTournamentMembershipInline' from 'federation.models.tournament'`.

- [ ] **Step 3: Add the inline and register it**

In `federation/models/tournament.py`, insert right after the `# Classes for admin` comment (currently line 601), before `class ArbiterTournamentMembershipInline(...)` (currently line 602):

```python
class OrganizerTournamentMembershipInline(RestrictedRelatedWidgetAdminMixin, admin.TabularInline):
    model = OrganizerTournamentMembership
    extra = 0
    autocomplete_fields = ['organizer']

    class Meta:
        verbose_name = 'Організатори турніру'
        verbose_name_plural = 'Організатори турніру'
```

Then modify `ArbiterTeamTournamentAdminInline.inlines` (currently line 624):

```python
    inlines = (OrganizerTournamentMembershipInline, ArbiterTournamentMembershipInline, TeamsTournamentMembershipInline,)
```

(Registered first so it matches the "Organizers and arbiters" heading order used on the public delegations page in Task 3. `RestrictedRelatedWidgetAdminMixin` already strips add/delete shortcuts from the widget generically — no further change needed there.)

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.OrganizerTournamentMembershipAdminTests -v 2`
Expected: `OK` (3 tests)

- [ ] **Step 5: Run the admin regression tests**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.RestrictedRelatedWidgetAdminMixinTests federation.tests.TeamTournamentMembershipCoachAdminTests federation.tests.TournamentPowerAdminActionTests -v 2`
Expected: `OK` — `save_formset`'s power-recalculation-on-change behavior is untouched by this task; organizer membership isn't part of `recalculate_power_for_current_state()`.

- [ ] **Step 6: Commit**

```bash
git add components/web-api/application/federation/models/tournament.py \
        components/web-api/application/federation/tests.py
git commit -m "feat(admin): manage tournament co-organizers via a new inline"
```

---

### Task 3: Show co-organizers on the tournament delegations page

**Files:**
- Modify: `components/web-api/application/federation/views/tournaments.py:5` (import), `:993` (query), `:1014-1021` (context)
- Modify: `components/web-api/application/federation/templates/tournaments/tournament.html:19`
- Modify: `components/web-api/application/federation/templates/tournaments/tournament_delegations.html`
- Test: `components/web-api/application/federation/tests.py`

**Interfaces:**
- Consumes: Task 1's `OrganizerTournamentMembership`.
- Produces: `organizers` context variable on the `tournament()` view — a queryset of `OrganizerTournamentMembership` filtered to the requested tournament, `select_related('organizer', 'organizer__current_club')`. Leaf/display feature — nothing later consumes it.

- [ ] **Step 1: Write the failing test**

Add a new test class right after `TournamentPageCoachDisplayTests` (currently ends at line 1818), before `class TournamentTeamExportCsvTests(TestCase):` (currently line 1820):

```python
class TournamentDelegationsOrganizerDisplayTests(TestCase):
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
            name='Delegations Organizer Cup',
            category='open',
            place='Kyiv',
            start_date=date(2026, 6, 1),
            format='swiko',
        )

    def test_tournament_page_shows_co_organizer_card_without_main_organizer(self):
        tournament = self.create_tournament()
        co_organizer = self.create_player('delegations-co-organizer')
        OrganizerTournamentMembership.objects.create(tournament=tournament, organizer=co_organizer)

        response = self.client.get('/tournament/{}'.format(tournament.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tournament-person-card-organizer')
        self.assertContains(response, co_organizer.get_name())
        self.assertContains(response, '/player/{}'.format(co_organizer.pk))
        self.assertNotContains(response, 'tournament-detail-empty-card')

    def test_tournament_page_shows_both_main_organizer_and_co_organizer(self):
        tournament = self.create_tournament()
        main_organizer = self.create_player('delegations-main-organizer')
        co_organizer = self.create_player('delegations-second-co-organizer')
        tournament.main_organizer = main_organizer
        tournament.save(update_fields=['main_organizer'])
        OrganizerTournamentMembership.objects.create(tournament=tournament, organizer=co_organizer)

        response = self.client.get('/tournament/{}'.format(tournament.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, main_organizer.get_name())
        self.assertContains(response, co_organizer.get_name())
        self.assertContains(response, 'tournament-person-card-organizer', count=2)

    def test_tournament_page_empty_state_unaffected_without_any_organizers_or_arbiters(self):
        tournament = self.create_tournament()

        response = self.client.get('/tournament/{}'.format(tournament.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tournament-detail-empty-card')

    def test_organizer_role_label_uses_get_role_display(self):
        tournament = self.create_tournament()
        co_organizer = self.create_player('delegations-role-label-organizer')
        OrganizerTournamentMembership.objects.create(tournament=tournament, organizer=co_organizer)

        with override('uk'):
            response = self.client.get('/tournament/{}'.format(tournament.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Організатор')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TournamentDelegationsOrganizerDisplayTests -v 2`
Expected: FAIL (3 of 4) — `test_tournament_page_shows_co_organizer_card_without_main_organizer`, `test_tournament_page_shows_both_main_organizer_and_co_organizer`, and `test_organizer_role_label_uses_get_role_display` all fail because no co-organizer card is rendered yet (the tournament falls back to the empty-state card, since there's no `main_organizer` and `organizers` isn't queried or passed to the template). `test_tournament_page_empty_state_unaffected_without_any_organizers_or_arbiters` already passes — it's a regression guard on existing behavior, not new behavior — which is expected and fine.

- [ ] **Step 3: Query co-organizers in the view**

In `federation/views/tournaments.py`, update the import (currently line 5):

```python
from federation.models.tournament import Tournament, ArbiterTournamentMembership, OrganizerTournamentMembership, TeamTournamentMembership
```

Add the query right after the existing `arbiters` line (currently line 993):

```python
    arbiters = ArbiterTournamentMembership.objects.filter(tournament=tournament).select_related('arbiter')
    organizers = OrganizerTournamentMembership.objects.filter(tournament=tournament).select_related('organizer', 'organizer__current_club')
```

Add it to the render context (currently lines 1014-1021):

```python
    return render(request, 'tournaments/tournament.html', {
        'tournament': tournament,
        'tournament_detail': _build_tournament_detail(tournament),
        'arbiters': arbiters,
        'organizers': organizers,
        'teams': teams,
        'page_title': _("Competitions"),
        'current_user': current_user,
    })
```

- [ ] **Step 4: Pass `organizers` into the delegations include**

In `federation/templates/tournaments/tournament.html`, modify (currently line 19):

```django
    {% include "tournaments/tournament_delegations.html" with tournament=tournament arbiters=arbiters organizers=organizers %}
```

- [ ] **Step 5: Render co-organizer cards**

In `federation/templates/tournaments/tournament_delegations.html`, change the guard condition (currently line 12):

```django
    {% if tournament.main_organizer or organizers or arbiters %}
```

Then insert a new loop right after the `main_organizer` card's `{% endif %}` (currently line 16), before the `arbiters` loop (currently line 18):

```django
        {% for membership in organizers %}
            {% include "tournaments/_tournament_person_card.html" with person=membership.organizer role_label=membership.get_role_display role_icon="bi-person-check" card_class="tournament-person-card-organizer" %}
        {% endfor %}
```

(Using `membership.get_role_display` instead of a static `{% trans %}` constant, unlike `main_organizer_label`/`arbiter_label` — this means a future second `ROLES` entry displays correctly with no template change. `card_class="tournament-person-card-organizer"` reuses the exact class already used for `main_organizer`, so no new CSS is needed.)

- [ ] **Step 6: Run test to verify it passes**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TournamentDelegationsOrganizerDisplayTests -v 2`
Expected: `OK` (4 tests)

- [ ] **Step 7: Run the broader tournament-page test suite to check for regressions**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TournamentListingPageTests federation.tests.TournamentPageCoachDisplayTests -v 2`
Expected: `OK`

- [ ] **Step 8: Manually verify in the browser**

Start the stack if it isn't running (`./deploy/local_run.sh`), open Django admin (`http://localhost:60102/admin/federation/tournament/<id>/change/`) for an existing tournament, add a co-organizer row via the new "Організатори турніру" inline and save, then open `http://localhost:60102/tournament/<id>` and confirm:
- The co-organizer's card appears in the "Organizers and arbiters" section, styled the same as the main organizer's card.
- If the tournament also has a `main_organizer`, both cards appear side by side.
- A tournament with no organizers or arbiters at all still shows the existing empty-state card.

- [ ] **Step 9: Commit**

```bash
git add components/web-api/application/federation/views/tournaments.py \
        components/web-api/application/federation/templates/tournaments/tournament.html \
        components/web-api/application/federation/templates/tournaments/tournament_delegations.html \
        components/web-api/application/federation/tests.py
git commit -m "feat(tournament): show co-organizers on the delegations page"
```

---

### Task 4: Translations

**Files:**
- Modify: `components/web-api/application/locale/uk/LC_MESSAGES/django.po` and `.mo`
- Modify: `components/web-api/application/locale/en/LC_MESSAGES/django.po` and `.mo`

**Interfaces:**
- Consumes: the `_('Organizer')` and `_('Role')` strings introduced on `OrganizerTournamentMembership` in Task 1. No new interfaces produced — this is the final task.

**Note:** both `msgid "Organizer"` and `msgid "Role"` already exist, fully translated, in both locale files (`"Organizer"` → `"Організатор"`/`"Organizer"`; `"Role"` → `"Роль"`/`"Role"`), from unrelated existing template strings. `makemessages` will merge the new source references onto these existing entries automatically — no new empty `msgstr` should appear, and no manual translation is needed.

- [ ] **Step 1: Regenerate the `.po` files**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py makemessages -l uk -l en`
Expected: `processing locale uk` / `processing locale en`, and `git diff` on both `django.po` files shows only new `#:` comment lines added under the existing `msgid "Organizer"` and `msgid "Role"` entries, pointing at `federation/models/tournament.py`. No new `msgid`/`msgstr` pair should appear.

- [ ] **Step 2: Verify no new empty translation was introduced**

Run: `git diff components/web-api/application/locale/uk/LC_MESSAGES/django.po components/web-api/application/locale/en/LC_MESSAGES/django.po`
Expected: only added `#:` reference lines; no line reading `msgstr ""` appears in the diff. If one does, the string isn't actually reusing an existing translation — stop and re-check the model's `_()` call.

- [ ] **Step 3: Compile messages**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py compilemessages`
Expected: `processing file django.po in .../locale/uk/LC_MESSAGES` / `... locale/en/LC_MESSAGES`, regenerating both `.mo` files.

- [ ] **Step 4: Run the full test suite one last time**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py check && docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation`
Expected: `OK`, no failures anywhere in the app.

- [ ] **Step 5: Commit**

```bash
git add components/web-api/application/locale/uk/LC_MESSAGES/django.po \
        components/web-api/application/locale/uk/LC_MESSAGES/django.mo \
        components/web-api/application/locale/en/LC_MESSAGES/django.po \
        components/web-api/application/locale/en/LC_MESSAGES/django.mo
git commit -m "i18n(tournament): register co-organizer source references"
```

---

## After all tasks

Follow `superpowers:finishing-a-development-branch` to decide how to integrate `feat/tournament-multiple-organizers`.
