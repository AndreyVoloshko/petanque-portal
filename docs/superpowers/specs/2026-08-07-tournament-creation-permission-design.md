# Tournament Creation Permission — Design

## Problem

`can_create_tournament` (`federation/permissions.py`) gates the "Add" button in
the `Tournament` admin and the "Додати турнір" shortcut on the public
tournaments listing page behind a hardcoded set of five `(id, username)`
pairs (`CREATE_TOURNAMENT_ALLOWLIST`). Changing who can create a tournament
requires editing this file and deploying. This surfaced as a live incident:
after the production database moved to a new server, a superuser who should
have had access no longer matched an allowlist entry, and there was no way to
grant access without a code change.

## Scope

In scope: replacing the hardcoded allowlist with Django's built-in per-model
permission (`federation.add_tournament`, auto-created for every model),
manageable entirely from the existing Django admin Users/Groups screens — no
new models, views, or admin UI. A one-time data migration preserves access
for the users currently on the allowlist.

Out of scope: any new UI for managing this permission (the standard
admin Users/Groups screens already do this); changes to any other
`Tournament` permission (`change`, `delete`, `view`); the unrelated
`OrganizerTournamentMembership` co-organizer work (separate spec, does not
touch this permission).

## Requirements (confirmed with stakeholder)

- **Access model**: stays a separately-managed grant, not folded into some
  other existing flag — but implemented using Django's *standard* permission
  semantics, including its automatic superuser bypass (any superuser can
  create tournaments; non-superusers need `add_tournament` granted
  explicitly). Confirmed: the extra "even superusers need an explicit grant"
  restriction from the old allowlist is intentionally dropped — not worth a
  custom permission-check that fights Django's normal behavior for this.
- **No new abstraction**: once the admin's `has_add_permission` override is
  removed, only one call site (`views/tournaments.py`) remains. A dedicated
  `permissions.py` module wrapping a single `has_perm()` call is unnecessary
  indirection — confirmed with stakeholder to delete the file entirely and
  inline the check.
- **Continuity for existing users**: the 5 people currently on the allowlist
  should not lose access as a side effect of this change. Confirmed: handled
  via a one-time data migration granting `add_tournament` explicitly, not a
  manual post-deploy step.
- **Migration safety**: given the recent server-migration incident where
  sequences (and potentially row identity) were affected, the data migration
  must not blindly trust that `user.id` still refers to the same person — it
  verifies `username` still matches before granting.

## Approach

**Chosen: Django's built-in per-model `add_tournament` permission**, checked
via `request.user.has_perm('federation.add_tournament')`, granted/revoked
through the standard admin Users (`user_permissions`) or Groups screens.

**Rejected: keep a custom `permissions.py` helper.** With the admin override
removed, there is exactly one caller left; a one-line wrapper module around
`has_perm()` adds a file and an import for no remaining logic.

**Rejected: a new dedicated model/table for "tournament organizers."** Django
already ships an equivalent mechanism (per-model permissions + Groups); a new
model would duplicate it for no added capability this project needs.

**Rejected: custom permission bypassing the superuser shortcut.** Would
require re-implementing part of `ModelBackend` semantics by hand to exclude
`is_superuser`. Confirmed with stakeholder this extra restriction isn't worth
preserving.

## Design

### 1. Remove the admin override (`federation/models/tournament.py`)

Delete `ArbiterTeamTournamentAdminInline.has_add_permission` (currently
line 674-675) and the now-unused
`from federation.permissions import can_create_tournament` import (line 18).
Django's default `ModelAdmin.has_add_permission` already checks
`request.user.has_perm('federation.add_tournament')` — identical behavior,
zero custom code.

### 2. Inline the check on the public listing page (`federation/views/tournaments.py`)

Replace the import and call (currently line 28 and line 97) with:

```python
'can_create_tournament': request.user.has_perm('federation.add_tournament'),
```

### 3. Delete `federation/permissions.py` entirely

No remaining callers after steps 1–2.

### 4. Data migration — preserve access for currently-allowlisted users

New migration in `federation/migrations/` (next after
`0077_teamtournamentmembership_coach.py`), `RunPython`, no schema change:

```python
from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

ALLOWLIST = [
    (1, "andreyvoloshko"),
    (65, "andriikamenev"),
    (84, "olenakolodiy"),
    (1084, "vsevolodprahnіtskij"),
    (1839, "admin"),
]


def grant_add_tournament_permission(apps, schema_editor):
    # On a fresh database (e.g. CI's test runner), Django's post_migrate
    # signal — which normally creates each model's add/change/delete/view
    # permissions — hasn't fired yet at this point in the same migrate batch.
    # Create permissions for the federation app explicitly first; this is a
    # no-op (get_or_create under the hood) when they already exist, as they
    # always will in production.
    for app_config in global_apps.get_app_configs():
        if app_config.label != 'federation':
            continue
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    User = apps.get_model('auth', 'User')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    tournament_ct = ContentType.objects.get(app_label='federation', model='tournament')
    permission = Permission.objects.get(content_type=tournament_ct, codename='add_tournament')

    for user_id, username in ALLOWLIST:
        user = User.objects.filter(id=user_id).first()
        if user is None:
            print(f'WARNING: no user with id={user_id} (expected username={username!r}); skipped.')
            continue
        if user.username != username:
            print(
                f'WARNING: user id={user_id} has username={user.username!r}, '
                f'expected {username!r}; skipped to avoid granting the wrong account.'
            )
            continue
        user.user_permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [
        ('federation', '0077_teamtournamentmembership_coach'),
    ]

    operations = [
        migrations.RunPython(grant_add_tournament_permission, migrations.RunPython.noop),
    ]
```

(Confirmed against `api/settings.py`: no `AUTH_USER_MODEL` override is set,
so the project uses Django's stock `auth.User` — `apps.get_model('auth',
'User')` above is correct as written.)

### 5. Testing (`federation/tests.py`)

- Remove the `can_create_tournament` import and the now-obsolete
  `test_permission_helper_requires_active_allowlisted_superuser` unit test
  (no standalone helper left to test in isolation).
- Rewrite `test_create_button_is_visible_only_for_allowlisted_superuser` →
  covers the new model: button visible for a superuser; button visible for a
  non-superuser explicitly granted `add_tournament`; button hidden for a
  plain authenticated user with neither.
- New test: `GET /admin/federation/tournament/add/` returns `200` for a user
  with the permission (or superuser) and `403` for a user without it —
  regression coverage for the behavior now fully delegated to Django's
  default `ModelAdmin.has_add_permission`, which had no direct test before.
- New test for the data migration: given users matching all 5 allowlist
  entries, all receive the permission; given a user id whose username
  doesn't match, that entry is skipped and the mismatched user does **not**
  receive the permission.

## Non-goals / explicitly out of scope

- No new admin screen or model for managing this permission — standard
  Django Users/Groups screens are the intended management surface.
- No change to `change_tournament`, `delete_tournament`, or
  `view_tournament` permissions.
- No change to `OrganizerTournamentMembership` / co-organizer display work
  (separate, already-specced project).
