# Player Profile Self-Service Insurance Date Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a player edit their own `insurance_expiration_date` from the self-service profile page (`/profile/`), with a valid/expired/none status badge next to it.

**Architecture:** Extend the existing `PlayerForm` (one `ModelForm`, one Save button, one `views/profile.py` code path) rather than adding a second form. Add the field to the existing crispy layout in its own visually separated row, with a small included template rendering the status badge. Register the field with the existing player-audit-trail constant list so the existing `record_player_change()` call (already invoked on every profile save) picks it up for free.

**Tech Stack:** Django 5 ModelForm + django-crispy-forms (bootstrap5 pack), Django's test client / `TestCase`, gettext i18n (`locale/{uk,en}/LC_MESSAGES/django.po`).

Design doc: [`docs/superpowers/specs/2026-08-04-player-profile-insurance-date-design.md`](../specs/2026-08-04-player-profile-insurance-date-design.md)

## Global Constraints

- No date validation beyond "is a valid date" — past dates and dates arbitrarily far in the future are both accepted. Do not add a `clean_insurance_expiration_date` validator.
- The field must be clearable back to blank by the player (it does not become required once set).
- One form, one Save button — do not add a second `<form>`/POST branch to `views/profile.py`.
- No migration needed — `insurance_expiration_date` already exists on `Player` (`federation/models/player.py:73`).
- `has_valid_insurance()` remains advisory-only; do not change its semantics or add a hard gate anywhere.
- Ukrainian-locale convention: every new user-visible string is wrapped in `_()`/`{% trans %}` and gets entries in both `locale/uk/LC_MESSAGES/django.po` and `locale/en/LC_MESSAGES/django.po`, followed by `compilemessages`.
- Run all commands (`test`, `compilemessages`, `check`) inside the running container: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py <command>`.

---

### Task 1: Make `insurance_expiration_date` an editable `PlayerForm` field

**Files:**
- Modify: `components/web-api/application/federation/forms/player_form.py`
- Test: `components/web-api/application/federation/tests.py` (class `PlayerLicenseListTests`, starting around line 723)

**Interfaces:**
- Produces: `PlayerForm.Meta.fields` now includes `'insurance_expiration_date'`; the crispy layout renders it in its own row (`Div('insurance_expiration_date', css_class="col-lg-4")`) inside a new top-level `Div` placed between the existing personal-info `Div` and the `Submit` `Div`. Task 2 depends on this row existing so it can add a sibling column with the status badge.

- [ ] **Step 1: Modify the existing test to expect the field, and add three new tests**

Open `components/web-api/application/federation/tests.py`. Find `test_profile_form_save_preserves_non_profile_fields` inside `class PlayerLicenseListTests(TestCase):` (currently around line 770). Replace it with:

```python
    def test_profile_form_save_preserves_non_profile_fields(self):
        player = self.create_player('licensed-profile', licence_number_value='00001')
        player.prefred_position = 'point'
        player.save()
        form = PlayerForm(data={
            'name': player.name,
            'surname': player.surname,
            'second_name': '',
            'birth_date': '1990-01-01',
            'current_club': '',
            'country': 'UA',
            'gender': player.gender,
            'facebook': '',
            'twitter': '',
            'instagram': '',
            'website': '',
            'email': 'licensed-profile@example.com',
            'insurance_expiration_date': '',
        }, instance=player)

        self.assertNotIn('licence_number', form.fields)
        self.assertNotIn('prefred_position', form.fields)
        self.assertIn('insurance_expiration_date', form.fields)
        self.assertTrue(form.is_valid(), form.errors)

        form.save()
        player.refresh_from_db()

        self.assertEqual(player.licence_number, '00001')
        self.assertTrue(player.is_licence_active)
        self.assertEqual(player.prefred_position, 'point')

    def test_profile_form_updates_insurance_expiration_date(self):
        player = self.create_player('insurance-update-player')
        new_date = timezone.localdate() + timedelta(days=400)
        form = PlayerForm(data={
            'name': player.name,
            'surname': player.surname,
            'second_name': '',
            'birth_date': '1990-01-01',
            'current_club': '',
            'country': 'UA',
            'gender': player.gender,
            'facebook': '',
            'twitter': '',
            'instagram': '',
            'website': '',
            'email': 'insurance-update-player@example.com',
            'insurance_expiration_date': new_date.strftime('%Y-%m-%d'),
        }, instance=player)

        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        player.refresh_from_db()

        self.assertEqual(player.insurance_expiration_date, new_date)

    def test_profile_form_accepts_past_insurance_expiration_date(self):
        player = self.create_player('insurance-past-player')
        past_date = timezone.localdate() - timedelta(days=10)
        form = PlayerForm(data={
            'name': player.name,
            'surname': player.surname,
            'second_name': '',
            'birth_date': '1990-01-01',
            'current_club': '',
            'country': 'UA',
            'gender': player.gender,
            'facebook': '',
            'twitter': '',
            'instagram': '',
            'website': '',
            'email': 'insurance-past-player@example.com',
            'insurance_expiration_date': past_date.strftime('%Y-%m-%d'),
        }, instance=player)

        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        player.refresh_from_db()

        self.assertEqual(player.insurance_expiration_date, past_date)

    def test_profile_form_clears_insurance_expiration_date(self):
        player = self.create_player('insurance-clear-player')
        player.insurance_expiration_date = timezone.localdate() + timedelta(days=30)
        player.save()

        form = PlayerForm(data={
            'name': player.name,
            'surname': player.surname,
            'second_name': '',
            'birth_date': '1990-01-01',
            'current_club': '',
            'country': 'UA',
            'gender': player.gender,
            'facebook': '',
            'twitter': '',
            'instagram': '',
            'website': '',
            'email': 'insurance-clear-player@example.com',
            'insurance_expiration_date': '',
        }, instance=player)

        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        player.refresh_from_db()

        self.assertIsNone(player.insurance_expiration_date)
```

(`timezone` and `timedelta` are already imported at the top of `tests.py`; no new imports needed.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.PlayerLicenseListTests -v 2`

Expected: `test_profile_form_save_preserves_non_profile_fields` FAILs on `self.assertIn('insurance_expiration_date', form.fields)` (field doesn't exist on the form yet), and the three new tests FAIL/ERROR because `insurance_expiration_date` isn't a valid form field (extra-data or missing-field errors).

- [ ] **Step 3: Add the field to `PlayerForm`**

In `components/web-api/application/federation/forms/player_form.py`, update `Meta`:

```python
    class Meta:
        model = Player
        fields = ('avatar',
                  'name',
                  'surname',
                  'second_name',
                  'birth_date',
                  'current_club',
                  'country',
                  'gender',
                  'facebook',
                  'twitter',
                  'instagram',
                  'website',
                  'insurance_expiration_date')
        labels = {
            "email": _("Email address"),
            "avatar": _("Avatar"),
            "name": _("First name"),
            "surname": _("Last name"),
            "second_name": _("Middle name"),
            "birth_date": _("Date of birth (dd.mm.yyyy)"),
            "current_club": _("Club"),
            "country": _("Country"),
            "gender": _("Gender"),
            "facebook": _("Facebook page"),
            "twitter": _("Twitter page"),
            "instagram": _("Instagram page"),
            "website": _("Personal website"),
            "insurance_expiration_date": _("Insurance valid until"),
        }
        widgets = {
            'avatar': ImageThumbnailFileInput,
        }
```

(`insurance_expiration_date` is `blank=True, null=True` on the model, so Django's `ModelForm` already infers `required=False` — no explicit field redeclaration needed, matching how `second_name`/`current_club`/`facebook`/`twitter`/`instagram`/`website` are handled today.)

Then update the crispy `Layout` in `PlayerForm.__init__` to add a new row between the personal-info `Div` and the `Submit` `Div`:

```python
        self.helper.layout = Layout(
            Div(
                Div(
                    Field('avatar', template="forms/profile/image_field.html",
                          avatar=self.instance.avatar,
                          attrs={'class': 'form-control', 'avatar': self.instance.avatar},
                          widget=ImageThumbnailFileInput()
                    ),
                    css_class="col-lg-2"
                ),
                Div(
                    Div(
                        Div('name', css_class="col-lg-4"),
                        Div('surname', css_class="col-lg-4"),
                        Div('second_name', css_class="col-lg-4"),
                        css_class="row"
                    ),
                    Div(
                        Div('email', css_class="col-lg-4"),
                        Div('gender', css_class="col-lg-4"),
                        Div('birth_date', css_class="col-lg-4"),
                        css_class="row"
                    ),
                    Div(
                        Div('current_club', css_class="col-lg-6"),
                        Div('country', css_class="col-lg-6"),
                        css_class="row"
                    ),
                    Div(
                        Div('facebook', css_class="col-lg-6"),
                        Div('instagram', css_class="col-lg-6"),
                        css_class="row"
                    ),
                    Div(
                        Div('twitter', css_class="col-lg-6"),
                        Div('website', css_class="col-lg-6"),
                        css_class="row"
                    ),
                    css_class="col-lg-10"
                ),
                css_class="row"
            ),
            Div(
                HTML('<hr class="my-2">'),
                Div(
                    Div('insurance_expiration_date', css_class="col-lg-4"),
                    css_class="row"
                ),
                css_class="col-lg-12"
            ),
            Div(
                Submit('submit', _('Save'), css_class='btn btn-success'),
                css_class="col-lg-12 text-center mb-3"
            )
        )
```

(`HTML` is already imported at the top of the file: `from crispy_forms.layout import Layout, Submit, Div, HTML, Field`.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.PlayerLicenseListTests federation.tests.PlayerProfileFormTests -v 2`

Expected: PASS (all of `PlayerLicenseListTests` including the 4 tests above, and `PlayerProfileFormTests.test_profile_form_layout_renders_every_bound_field`, which now passes because `insurance_expiration_date` is in both `form.fields` and the layout).

- [ ] **Step 5: Commit**

```bash
git add components/web-api/application/federation/forms/player_form.py components/web-api/application/federation/tests.py
git commit -m "feat(profile): let players edit their own insurance expiration date"
```

- [ ] **Step 6 (addendum, added after user request mid-implementation): use a native HTML5 date picker**

The user asked for the field to render as a datepicker "in an easy way." The simplest option
requiring no new JS dependency is Django's built-in support for HTML5 `<input type="date">`,
which every modern browser renders with its own native calendar picker. Add a widget override
to `Meta.widgets` in `components/web-api/application/federation/forms/player_form.py`:

```python
        widgets = {
            'avatar': ImageThumbnailFileInput,
            'insurance_expiration_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }
```

(`forms` is already imported at the top of the file: `from django import forms`.) HTML5 date
inputs always submit `YYYY-MM-DD`, which matches the `.strftime('%Y-%m-%d')` format the Task 1
tests already POST — no test changes needed for submission. The explicit `format='%Y-%m-%d'` is
required for *rendering* too: without it, Django renders an existing value through the active
locale's display format (e.g. `dd.mm.yyyy` under `uk`), which is invalid for an HTML5
`type="date"` input's `value` attribute — browsers silently discard it and show the picker
empty even though the player already has a date on file, risking silent data loss if they save
without noticing. (Caught in task review; fixed with a regression test,
`test_profile_form_renders_existing_insurance_expiration_date_in_iso_format`, asserting the
rendered widget contains `value="2026-09-03"` for a player whose `insurance_expiration_date` is
already set to `date(2026, 9, 3)`.) Re-run the Step 4 test command to confirm nothing broke,
then commit:

```bash
git add components/web-api/application/federation/forms/player_form.py components/web-api/application/federation/tests.py
git commit -m "feat(profile): use native HTML5 date picker for insurance date input"
git commit -m "fix(profile): render existing insurance date in ISO format for date input"
```

---

### Task 2: Add the insurance status badge

**Files:**
- Create: `components/web-api/application/federation/templates/forms/profile/insurance_status.html`
- Modify: `components/web-api/application/federation/forms/player_form.py`
- Test: `components/web-api/application/federation/tests.py` (class `PlayerProfileFormTests`, starting around line 712)

**Interfaces:**
- Consumes: the `insurance_expiration_date` row added in Task 1 (`Div('insurance_expiration_date', css_class="col-lg-4")` inside the new insurance `Div`).
- Produces: a `player` context variable passed into `insurance_status.html`, backed by `Player.has_valid_insurance()` (`federation/models/player.py:136`) and `Player.insurance_expiration_date` (`federation/models/player.py:73`). Task 4 (translations) depends on the exact `{% trans %}` strings used here: `"Valid until"`, `"Expired"`, `"No insurance on file"`.

- [ ] **Step 1: Write the failing tests**

Add to `class PlayerProfileFormTests(TestCase):` in `components/web-api/application/federation/tests.py` (after `test_profile_form_layout_renders_every_bound_field`):

```python
    def create_player_with_insurance(self, username, insurance_expiration_date=None):
        user = User.objects.create_user(username=username, password='Pass1234!')
        Player.objects.create(
            user=user,
            name='Badge',
            surname=username.title(),
            birth_date=date(1990, 1, 1),
            gender='M',
            country='UA',
            insurance_expiration_date=insurance_expiration_date,
        )
        return user

    def test_profile_page_shows_valid_insurance_badge(self):
        valid_until = timezone.localdate() + timedelta(days=30)
        self.create_player_with_insurance('badge-valid-player', valid_until)
        self.client.login(username='badge-valid-player', password='Pass1234!')

        with override('en'):
            response = self.client.get('/profile/')

        self.assertContains(response, 'Valid until')
        self.assertContains(response, valid_until.strftime('%d.%m.%Y'))
        self.assertContains(response, 'text-success')

    def test_profile_page_shows_expired_insurance_badge(self):
        expired_on = timezone.localdate() - timedelta(days=5)
        self.create_player_with_insurance('badge-expired-player', expired_on)
        self.client.login(username='badge-expired-player', password='Pass1234!')

        with override('en'):
            response = self.client.get('/profile/')

        self.assertContains(response, 'Expired')
        self.assertContains(response, expired_on.strftime('%d.%m.%Y'))
        self.assertContains(response, 'text-danger')

    def test_profile_page_shows_no_insurance_badge_when_blank(self):
        self.create_player_with_insurance('badge-none-player')
        self.client.login(username='badge-none-player', password='Pass1234!')

        with override('en'):
            response = self.client.get('/profile/')

        self.assertContains(response, 'No insurance on file')
        self.assertContains(response, 'text-muted')
```

(`User`, `Player`, `date`, `timezone`, `timedelta`, `override` are already imported at the top of `tests.py`.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.PlayerProfileFormTests -v 2`

Expected: the three new tests FAIL — none of "Valid until" / "Expired" / "No insurance on file" / `text-success` / `text-danger` / `text-muted` appear in the response yet.

- [ ] **Step 3: Create the status badge template**

Create `components/web-api/application/federation/templates/forms/profile/insurance_status.html`:

```html
{% load i18n %}
{% if player.insurance_expiration_date %}
    {% if player.has_valid_insurance %}
        <span class="text-success">{% trans "Valid until" %} {{ player.insurance_expiration_date|date:"d.m.Y" }}</span>
    {% else %}
        <span class="text-danger">{% trans "Expired" %} {{ player.insurance_expiration_date|date:"d.m.Y" }}</span>
    {% endif %}
{% else %}
    <span class="text-muted">{% trans "No insurance on file" %}</span>
{% endif %}
```

- [ ] **Step 4: Wire the badge into the layout**

In `components/web-api/application/federation/forms/player_form.py`, update the insurance `Div` added in Task 1 to add a sibling column with the badge include:

```python
            Div(
                HTML('<hr class="my-2">'),
                Div(
                    Div('insurance_expiration_date', css_class="col-lg-4"),
                    Div(
                        HTML('{% include "forms/profile/insurance_status.html" with player=form.instance %}'),
                        css_class="col-lg-8 d-flex align-items-center"
                    ),
                    css_class="row"
                ),
                css_class="col-lg-12"
            ),
```

(`django-crispy-forms`' `HTML` layout node renders with the full page context, which crispy always populates with `form` — see `crispy_forms/utils.py` — so `form.instance` resolves to the `Player` being edited without any other wiring.)

- [ ] **Step 5: Run the tests to verify they pass**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.PlayerProfileFormTests -v 2`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add components/web-api/application/federation/forms/player_form.py components/web-api/application/federation/templates/forms/profile/insurance_status.html components/web-api/application/federation/tests.py
git commit -m "feat(profile): show insurance valid/expired/none status badge"
```

---

### Task 3: Track insurance date changes in the audit trail

**Files:**
- Modify: `components/web-api/application/federation/audit/constants.py`
- Modify: `components/web-api/application/federation/audit/__init__.py`
- Test: `components/web-api/application/federation/test_audit.py` (class `PlayerProfileAuditLogTests`, starting around line 44)

**Interfaces:**
- Produces: `PLAYER_CHANGE_FIELD_INSURANCE_EXPIRATION_DATE = 'insurance_expiration_date'`, exported from `federation.audit` alongside the other `PLAYER_CHANGE_FIELD_*` constants, and included in `PLAYER_CHANGE_FIELDS`.

- [ ] **Step 1: Write the failing test**

Add to `class PlayerProfileAuditLogTests(TestCase):` in `components/web-api/application/federation/test_audit.py` (after `test_profile_country_change_creates_player_log_entry`):

```python
    def test_profile_insurance_expiration_date_change_creates_player_log_entry(self):
        user, player = self.create_player()
        new_date = timezone.localdate() + timedelta(days=200)
        self.client.login(username=user.username, password='OldPass123!')

        response = self.client.post('/profile/', {
            'name': player.name,
            'surname': player.surname,
            'second_name': '',
            'birth_date': '1990-01-01',
            'current_club': str(player.current_club_id),
            'country': 'UA',
            'gender': player.gender,
            'facebook': '',
            'twitter': '',
            'instagram': '',
            'website': '',
            'email': user.email,
            'insurance_expiration_date': new_date.strftime('%Y-%m-%d'),
        })

        self.assertEqual(response.status_code, 200)
        player.refresh_from_db()
        self.assertEqual(player.insurance_expiration_date, new_date)
        log_entry = LogEntry.objects.get()
        self.assertIn(PLAYER_CHANGE_FIELD_INSURANCE_EXPIRATION_DATE, self.get_changed_fields(log_entry))
        values = extract_changed_field_values(log_entry.change_message)
        self.assertEqual(values['insurance_expiration_date'], {'old': None, 'new': new_date.isoformat()})
```

Add `PLAYER_CHANGE_FIELD_INSURANCE_EXPIRATION_DATE` to the `from federation.audit import (...)` block near the top of `test_audit.py`:

```python
from federation.audit import (
    AUDIT_CHANGE_MESSAGE_VALUES_KEY,
    PLAYER_CHANGE_FIELD_AVATAR,
    PLAYER_CHANGE_FIELD_CURRENT_CLUB,
    PLAYER_CHANGE_FIELD_INSURANCE_EXPIRATION_DATE,
    PLAYER_CHANGE_FIELD_IS_LICENCE_ACTIVE,
    PLAYER_CHANGE_FIELD_PASSWORD,
    PLAYER_CHANGE_FIELD_SPORT_TITLE,
    PLAYER_CHANGE_FILTER_CLUB,
    PLAYER_CHANGE_IGNORED_FIELDS,
    PLAYER_CHANGE_MESSAGE_CHANGED_KEY,
    PLAYER_CHANGE_MESSAGE_FIELDS_KEY,
    SYSTEM_AUDIT_TOURNAMENT_RESULTS_USERNAME,
    TOURNAMENT_CHANGE_FIELD_TEAM_PLACES,
    capture_player_change_values,
    extract_changed_field_values,
    format_player_change_fields,
    get_player_change_filter_choices,
    get_revert_source_log_entry_id,
    log_model_change,
    log_player_change,
    record_model_change,
)
```

`date`, `timedelta`, `LogEntry` are already imported at the top of `test_audit.py`, but `timezone` is not — add it:

```python
from django.utils import timezone
from django.utils.translation import gettext as _, override
```

(insert the `timezone` import line right above the existing `from django.utils.translation import ...` line, near the top of `test_audit.py`.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.test_audit.PlayerProfileAuditLogTests.test_profile_insurance_expiration_date_change_creates_player_log_entry -v 2`

Expected: FAIL — `ImportError` (constant doesn't exist yet), or once the import is temporarily stubbed, the changed field is missing from the log entry because `capture_player_change_values()` only scans `PLAYER_CHANGE_FIELDS`, which doesn't include `insurance_expiration_date` yet.

- [ ] **Step 3: Register the field for audit tracking**

In `components/web-api/application/federation/audit/constants.py`, add the constant and include it in `PLAYER_CHANGE_FIELDS`:

```python
PLAYER_CHANGE_FIELD_AVATAR = 'avatar'
PLAYER_CHANGE_FIELD_CURRENT_CLUB = 'current_club'
PLAYER_CHANGE_FIELD_INSURANCE_EXPIRATION_DATE = 'insurance_expiration_date'
PLAYER_CHANGE_FIELD_IS_LICENCE_ACTIVE = 'is_licence_active'
PLAYER_CHANGE_FIELD_LICENCE_NUMBER = 'licence_number'
PLAYER_CHANGE_FIELD_PASSWORD = 'password'
PLAYER_CHANGE_FIELD_SPORT_TITLE = 'sport_title'
```

```python
PLAYER_CHANGE_FIELDS = (
    'user',
    PLAYER_CHANGE_FIELD_CURRENT_CLUB,
    PLAYER_CHANGE_FIELD_AVATAR,
    'name',
    'surname',
    'second_name',
    'birth_date',
    'email',
    PLAYER_CHANGE_FIELD_PASSWORD,
    'country',
    'gender',
    PLAYER_CHANGE_FIELD_LICENCE_NUMBER,
    PLAYER_CHANGE_FIELD_IS_LICENCE_ACTIVE,
    'is_inclusive',
    'prefred_position',
    'facebook',
    'twitter',
    'instagram',
    'website',
    'arbiter_level',
    'coach_level',
    PLAYER_CHANGE_FIELD_SPORT_TITLE,
    PLAYER_CHANGE_FIELD_INSURANCE_EXPIRATION_DATE,
)
```

In `components/web-api/application/federation/audit/__init__.py`, add the constant to both the import block and `__all__`:

```python
from .constants import (
    AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY,
    AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY,
    AUDIT_CHANGE_MESSAGE_SOURCE_LOG_ENTRY_ID_KEY,
    AUDIT_CHANGE_MESSAGE_VALUES_KEY,
    PLAYER_CHANGE_FIELD_AVATAR,
    PLAYER_CHANGE_FIELD_CURRENT_CLUB,
    PLAYER_CHANGE_FIELD_INSURANCE_EXPIRATION_DATE,
    PLAYER_CHANGE_FIELD_IS_LICENCE_ACTIVE,
    PLAYER_CHANGE_FIELD_PASSWORD,
    PLAYER_CHANGE_FIELD_SPORT_TITLE,
    PLAYER_CHANGE_FILTER_CLUB,
    PLAYER_CHANGE_IGNORED_FIELDS,
    PLAYER_CHANGE_MESSAGE_CHANGED_KEY,
    PLAYER_CHANGE_MESSAGE_FIELDS_KEY,
    SYSTEM_AUDIT_TOURNAMENT_DRAW_USERNAME,
    SYSTEM_AUDIT_TOURNAMENT_RESULTS_USERNAME,
    TOURNAMENT_CHANGE_FIELD_TEAM_PLACES,
)
```

```python
__all__ = [
    'AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY',
    'AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY',
    'AUDIT_CHANGE_MESSAGE_SOURCE_LOG_ENTRY_ID_KEY',
    'AUDIT_CHANGE_MESSAGE_VALUES_KEY',
    'PLAYER_CHANGE_FIELD_AVATAR',
    'PLAYER_CHANGE_FIELD_CURRENT_CLUB',
    'PLAYER_CHANGE_FIELD_INSURANCE_EXPIRATION_DATE',
    'PLAYER_CHANGE_FIELD_IS_LICENCE_ACTIVE',
    'PLAYER_CHANGE_FIELD_PASSWORD',
    'PLAYER_CHANGE_FIELD_SPORT_TITLE',
    'PLAYER_CHANGE_FILTER_CLUB',
    'PLAYER_CHANGE_IGNORED_FIELDS',
    'PLAYER_CHANGE_MESSAGE_CHANGED_KEY',
    'PLAYER_CHANGE_MESSAGE_FIELDS_KEY',
    'SYSTEM_AUDIT_TOURNAMENT_DRAW_USERNAME',
    'SYSTEM_AUDIT_TOURNAMENT_RESULTS_USERNAME',
    'TOURNAMENT_CHANGE_FIELD_TEAM_PLACES',
    'build_tournament_team_places_field_values',
    'capture_model_change_values',
    'capture_player_change_values',
    'extract_changed_field_values',
    'extract_changed_fields',
    'format_model_change_fields',
    'format_player_change_fields',
    'get_log_entry_object',
    'get_log_entry_revert_reason',
    'get_model_change_filter_choices',
    'get_model_change_filter_lookup_terms',
    'get_or_create_system_audit_user',
    'get_player_change_filter_choices',
    'get_revert_source_log_entry_id',
    'is_revert_change_message',
    'log_model_change',
    'log_player_change',
    'normalize_player_change_fields',
    'record_model_change',
    'record_player_change',
    'record_tournament_team_places_change',
    'replace_changed_fields_in_message',
    'revert_log_entry',
]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.test_audit.PlayerProfileAuditLogTests -v 2`

Expected: PASS (including the pre-existing tests in this class — confirms nothing else in `PLAYER_CHANGE_FIELDS` broke).

- [ ] **Step 5: Commit**

```bash
git add components/web-api/application/federation/audit/constants.py components/web-api/application/federation/audit/__init__.py components/web-api/application/federation/test_audit.py
git commit -m "feat(audit): track player self-service insurance date changes"
```

---

### Task 4: Add uk/en translations for the new status-badge strings

**Files:**
- Modify: `components/web-api/application/locale/uk/LC_MESSAGES/django.po`
- Modify: `components/web-api/application/locale/en/LC_MESSAGES/django.po`
- Generated: `components/web-api/application/locale/uk/LC_MESSAGES/django.mo`, `components/web-api/application/locale/en/LC_MESSAGES/django.mo` (via `compilemessages`, not hand-edited)
- Test: `components/web-api/application/federation/tests.py` (class `PlayerProfileFormTests`)

**Interfaces:**
- Consumes: the exact `{% trans %}` source strings from Task 2 — `"Valid until"`, `"Expired"`, `"No insurance on file"`. The field label `"Insurance valid until"` (used in `PlayerForm.Meta.labels` since Task 1) is already translated — it's the same string as `Player.insurance_expiration_date`'s model `verbose_name` (`federation/models/player.py:73`), already present in both `.po` files.

- [ ] **Step 1: Write the failing test**

Add to `class PlayerProfileFormTests(TestCase):` in `components/web-api/application/federation/tests.py` (after the badge tests added in Task 2):

```python
    def test_profile_page_shows_localized_insurance_badge_in_ukrainian(self):
        valid_until = timezone.localdate() + timedelta(days=30)
        self.create_player_with_insurance('badge-uk-player', valid_until)
        self.client.login(username='badge-uk-player', password='Pass1234!')

        with override('uk'):
            response = self.client.get('/profile/')

        self.assertContains(response, 'Дійсне до')
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.PlayerProfileFormTests.test_profile_page_shows_localized_insurance_badge_in_ukrainian -v 2`

Expected: FAIL — without a `uk` catalog entry, gettext falls back to the untranslated source string "Valid until", so "Дійсне до" is not in the response.

- [ ] **Step 3: Add the translation entries**

In `components/web-api/application/locale/uk/LC_MESSAGES/django.po`, add (near the existing insurance entries, e.g. after `msgid "Insurance is missing or expired"`):

```
#: federation/templates/forms/profile/insurance_status.html
msgid "Valid until"
msgstr "Дійсне до"

#: federation/templates/forms/profile/insurance_status.html
msgid "Expired"
msgstr "Прострочено"

#: federation/templates/forms/profile/insurance_status.html
msgid "No insurance on file"
msgstr "Страхування відсутнє"
```

In `components/web-api/application/locale/en/LC_MESSAGES/django.po`, add the equivalent identity entries:

```
#: federation/templates/forms/profile/insurance_status.html
msgid "Valid until"
msgstr "Valid until"

#: federation/templates/forms/profile/insurance_status.html
msgid "Expired"
msgstr "Expired"

#: federation/templates/forms/profile/insurance_status.html
msgid "No insurance on file"
msgstr "No insurance on file"
```

- [ ] **Step 4: Compile the message catalogs**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py compilemessages`

Expected: `processing file django.po in .../locale/uk/LC_MESSAGES` and the same for `en`, with no errors. This regenerates both `django.mo` files.

- [ ] **Step 5: Run the test to verify it passes**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.PlayerProfileFormTests -v 2`

Expected: PASS for the whole class, including the Task 2 English-language badge tests (unaffected) and the new Ukrainian test.

- [ ] **Step 6: Commit**

```bash
git add components/web-api/application/locale/uk/LC_MESSAGES/django.po components/web-api/application/locale/uk/LC_MESSAGES/django.mo components/web-api/application/locale/en/LC_MESSAGES/django.po components/web-api/application/locale/en/LC_MESSAGES/django.mo components/web-api/application/federation/tests.py
git commit -m "i18n(profile): translate insurance status badge strings"
```

---

### Task 5: Full-suite verification and manual browser check

**Files:** none (verification only).

- [ ] **Step 1: Run Django system checks**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py check`

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 2: Run the full test suite**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test`

Expected: all tests pass (0 failures), including the ~160+ pre-existing tests plus the 8 new ones added across Tasks 1, 2, and 4.

- [ ] **Step 3: Confirm no migration is needed**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py makemigrations --check --dry-run`

Expected: exits 0 with "No changes detected" — confirms the Global Constraint that no model change was made.

- [ ] **Step 4: Manual browser verification**

With the local stack running (`./deploy/local_run.sh`), log in as a test player at `http://localhost:60102/login/` and open `http://localhost:60102/profile/`. Confirm:
- The "Insurance valid until" field appears in its own row below the personal-info fields, above the Save button.
- With no date set, the badge reads "No insurance on file" (muted).
- Entering a future date and saving shows a green "Valid until <date>" badge after reload.
- Entering a past date and saving shows a red "Expired <date>" badge after reload.
- Clearing the field and saving returns the badge to "No insurance on file".
- Switching the site language to Ukrainian (existing language switcher) shows the Ukrainian translations from Task 4.

- [ ] **Step 5: No commit** — this task only verifies prior commits; if any step fails, fix the issue in the relevant task's files and re-run from Step 1.

---

## Finishing Up

Once Task 5 passes, push the branch and open a PR against `master`:

```bash
git push -u origin feat/player-profile-insurance-date
gh pr create --title "feat(profile): let players self-service their insurance expiration date" --body "$(cat <<'EOF'
## Summary
- Players can now set/update/clear their own `insurance_expiration_date` from the profile page, alongside a valid/expired/none status badge.
- Self-service edits are now tracked in the player audit trail (previously only admin edits were).
- New strings translated to Ukrainian and English.

## Test plan
- [x] `manage.py test federation.tests.PlayerLicenseListTests`
- [x] `manage.py test federation.tests.PlayerProfileFormTests`
- [x] `manage.py test federation.test_audit.PlayerProfileAuditLogTests`
- [x] `manage.py test` (full suite)
- [x] `manage.py check`
- [x] Manual verification in browser (set/clear/expired/valid badge states, uk/en)

Design doc: docs/superpowers/specs/2026-08-04-player-profile-insurance-date-design.md
EOF
)"
```
