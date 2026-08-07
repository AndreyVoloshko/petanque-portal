# Tournament Creation Permission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded `CREATE_TOURNAMENT_ALLOWLIST` (`federation/permissions.py`) with Django's built-in per-model `add_tournament` permission, so who can create a tournament is managed entirely from the Django admin's Users/Groups screens instead of requiring a code change and deploy.

**Architecture:** Delete the custom allowlist-checking function and its dedicated module. The admin's `has_add_permission` override is removed entirely (Django's default `ModelAdmin.has_add_permission` already checks `request.user.has_perm('federation.add_tournament')`, which is exactly the desired behavior). The one remaining caller (the public tournaments page, which shows/hides an "Add" shortcut) inlines the same `has_perm` check directly. A one-time data migration grants the permission to the 5 people currently on the allowlist so nobody loses access as a side effect.

**Tech Stack:** Django 5, PostgreSQL 17, `manage.py test`.

**Spec:** [`docs/superpowers/specs/2026-08-07-tournament-creation-permission-design.md`](../specs/2026-08-07-tournament-creation-permission-design.md)

## Global Constraints

- Any command below runs inside the running local stack container: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py <command>` (per `CLAUDE.md`). Start the stack first with `./deploy/local_run.sh` if it isn't already running.
- Never edit an existing migration file — always generate a new one with `makemigrations`.
- Django always grants superusers every permission automatically; this is intentional per the spec (the old allowlist's extra "even superusers need an explicit grant" restriction is dropped, confirmed with stakeholder).
- No new admin screen, model, or custom permission-check module — access is managed via Django's standard Users/Groups admin screens only (confirmed with stakeholder: a dedicated wrapper module for a single `has_perm()` call is unnecessary indirection).
- Commit after each task with a conventional commit message (`type(scope): description`).

---

### Task 1: Replace the allowlist with the standard `add_tournament` permission

**Files:**
- Modify: `components/web-api/application/federation/models/tournament.py:18` (remove import), `:673-676` (remove `has_add_permission` override)
- Modify: `components/web-api/application/federation/views/tournaments.py:28` (remove import), `:97` (inline the check)
- Delete: `components/web-api/application/federation/permissions.py`
- Modify: `components/web-api/application/federation/tests.py:16` (import), `:46` (remove import), `:3157-3208` (replace tests)

**Interfaces:**
- Produces: tournament-creation access is now determined solely by `request.user.has_perm('federation.add_tournament')` — Django's standard per-model permission, satisfied automatically for superusers and otherwise grantable via a user's "User permissions" field or a Group, both on the standard `/admin/auth/user/<id>/change/` and `/admin/auth/group/` screens. Task 2 consumes this exact permission string when writing the data migration.

- [ ] **Step 1: Write the failing tests**

In `federation/tests.py`, change the import on line 16 from:

```python
from django.contrib.auth.models import User
```

to:

```python
from django.contrib.auth.models import Permission, User
```

Remove line 46 (`from federation.permissions import can_create_tournament`) — it will have no replacement import; `can_create_tournament` is not referenced anywhere else in this file after this task.

Replace lines 3157-3208 (the `test_create_button_is_visible_only_for_allowlisted_superuser` and `test_permission_helper_requires_active_allowlisted_superuser` methods, i.e. everything between the preceding `test_english_listing_localizes_labels_and_keeps_key_based_filters` method and the module-level `_make_uploaded_image` function) with:

```python
    def test_create_button_is_visible_for_superuser(self):
        self.create_tournament('Future Cup')
        User.objects.create_superuser(
            username='any-superuser',
            email='any-superuser@example.com',
            password='secret',
        )

        self.client.login(username='any-superuser', password='secret')
        response = self.client.get('/tournaments/')

        self.assertContains(response, 'Додати турнір')

    def test_create_button_is_visible_for_non_superuser_with_explicit_permission(self):
        self.create_tournament('Future Cup')
        user = User.objects.create_user(
            username='granted-organizer',
            email='granted-organizer@example.com',
            password='secret',
        )
        permission = Permission.objects.get(content_type__app_label='federation', codename='add_tournament')
        user.user_permissions.add(permission)

        self.client.login(username='granted-organizer', password='secret')
        response = self.client.get('/tournaments/')

        self.assertContains(response, 'Додати турнір')

    def test_create_button_is_hidden_for_plain_authenticated_user(self):
        self.create_tournament('Future Cup')
        User.objects.create_user(
            username='plain-user',
            email='plain-user@example.com',
            password='secret',
        )

        self.client.login(username='plain-user', password='secret')
        response = self.client.get('/tournaments/')

        self.assertNotContains(response, 'Додати турнір')

    def test_admin_add_view_allows_user_with_permission(self):
        User.objects.create_superuser(
            username='admin-add-superuser',
            email='admin-add-superuser@example.com',
            password='secret',
        )
        self.client.login(username='admin-add-superuser', password='secret')

        response = self.client.get('/admin/federation/tournament/add/')

        self.assertEqual(response.status_code, 200)

    def test_admin_add_view_forbidden_without_permission(self):
        User.objects.create_user(
            username='admin-add-plain-staff',
            email='admin-add-plain-staff@example.com',
            password='secret',
            is_staff=True,
        )
        self.client.login(username='admin-add-plain-staff', password='secret')

        response = self.client.get('/admin/federation/tournament/add/')

        self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TournamentListingPageTests -v 2`
Expected: FAIL — `test_create_button_is_visible_for_superuser`, `test_create_button_is_visible_for_non_superuser_with_explicit_permission`, and `test_admin_add_view_allows_user_with_permission` fail because the old `can_create_tournament` still requires a hardcoded `(id, username)` allowlist match, which none of these fresh test users satisfy. `test_create_button_is_hidden_for_plain_authenticated_user` and `test_admin_add_view_forbidden_without_permission` already pass (correct behavior under the old code too) — expected, these are regression guards, not new behavior.

- [ ] **Step 3: Remove the admin override**

In `federation/models/tournament.py`, remove line 18:

```python
from federation.permissions import can_create_tournament
```

Then remove the `has_add_permission` method (currently lines 674-676, directly after `save_formset`):

```python
    def has_add_permission(self, request):
        return can_create_tournament(request.user)
```

`save_formset` should now be the last method on `ArbiterTeamTournamentAdminInline`, with no blank-line gap left behind before the class ends.

- [ ] **Step 4: Inline the check on the public listing page**

In `federation/views/tournaments.py`, remove line 28:

```python
from federation.permissions import can_create_tournament
```

Change line 97 from:

```python
        'can_create_tournament': can_create_tournament(request.user),
```

to:

```python
        'can_create_tournament': request.user.has_perm('federation.add_tournament'),
```

- [ ] **Step 5: Delete the now-unused module**

```bash
git rm components/web-api/application/federation/permissions.py
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TournamentListingPageTests -v 2`
Expected: `OK` (all tests in this class pass, including the 5 new ones)

- [ ] **Step 7: Run the full test suite and system checks to confirm no regressions**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py check && docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation`
Expected: `OK` — no other test references `can_create_tournament` or `federation.permissions` (confirmed by grep before writing this plan), so nothing else should be affected.

- [ ] **Step 8: Commit**

```bash
git add components/web-api/application/federation/models/tournament.py \
        components/web-api/application/federation/views/tournaments.py \
        components/web-api/application/federation/tests.py
git rm components/web-api/application/federation/permissions.py
git commit -m "feat(admin): replace tournament-creation allowlist with standard add_tournament permission"
```

---

### Task 2: Data migration — preserve access for currently-allowlisted users

**Files:**
- Create: `components/web-api/application/federation/migrations/0078_grant_tournament_creation_permission.py` (exact number may differ — use whatever `makemigrations --empty` generates; adjust the filename in Step 2's test and Step 5/6 commands to match)
- Test: `components/web-api/application/federation/tests.py`

**Interfaces:**
- Consumes: Task 1's `federation.add_tournament` permission as the access-control mechanism (this migration grants exactly that permission).
- Produces: a one-time, already-applied data migration. Nothing later in this plan consumes it — it's a leaf task.

- [ ] **Step 1: Generate the empty migration file**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py makemigrations federation --empty --name grant_tournament_creation_permission`
Expected: `Migrations for 'federation': federation/migrations/0078_grant_tournament_creation_permission.py` (or whatever number Django assigns — use the actual generated filename for every subsequent step in this task).

- [ ] **Step 2: Write the failing test**

Add a new test class to `federation/tests.py`, right after the `TournamentListingPageTests` class (after the last test method added in Task 1, before the module-level `_make_uploaded_image` function):

```python
class TournamentCreatePermissionMigrationTests(TestCase):
    def _run_migration(self):
        from django.apps import apps as global_apps
        from django.db import connection
        from django.db.migrations.loader import MigrationLoader

        loader = MigrationLoader(connection)
        migration = None
        for (app_label, name), candidate in loader.disk_migrations.items():
            if app_label == 'federation' and name.endswith('grant_tournament_creation_permission'):
                migration = candidate
                break
        self.assertIsNotNone(migration, 'migration grant_tournament_creation_permission not found on disk')

        forwards = migration.operations[0].code
        forwards(global_apps, None)

    def test_grants_permission_to_matching_allowlisted_users(self):
        allowlist = [
            (1, 'andreyvoloshko'),
            (65, 'andriikamenev'),
            (84, 'olenakolodiy'),
            (1084, 'vsevolodprahnіtskij'),
            (1839, 'admin'),
        ]
        for user_id, username in allowlist:
            User.objects.create_user(id=user_id, username=username)

        self._run_migration()

        for user_id, username in allowlist:
            user = User.objects.get(id=user_id)
            self.assertTrue(user.has_perm('federation.add_tournament'))

    def test_skips_user_whose_username_no_longer_matches(self):
        User.objects.create_user(id=65, username='someone-else-now')

        self._run_migration()

        user = User.objects.get(id=65)
        self.assertFalse(user.has_perm('federation.add_tournament'))

    def test_skips_missing_user_ids_without_error(self):
        self._run_migration()
```

(Uses the `MigrationLoader` to find the migration by its descriptive name suffix rather than hardcoding the numeric prefix, so this test doesn't need editing if the generated number differs from `0078`. `Permission` and `User` are already imported from Task 1.)

- [ ] **Step 3: Run the test to verify it fails**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TournamentCreatePermissionMigrationTests -v 2`
Expected: FAIL on `test_grants_permission_to_matching_allowlisted_users` — `AssertionError: False is not true`, because the generated migration file is still empty (`operations = []`), so `migration.operations[0]` raises `IndexError` (or the test fails outright before reaching the assertion). `test_skips_user_whose_username_no_longer_matches` and `test_skips_missing_user_ids_without_error` will also fail/error the same way, since all three call `_run_migration()`.

- [ ] **Step 4: Implement the migration**

Open the file generated in Step 1 (`federation/migrations/0078_grant_tournament_creation_permission.py` — use the actual generated filename) and replace its contents with:

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

(`dependencies` should already read `('federation', '0077_teamtournamentmembership_coach')` from the `--empty` scaffold if `0077` was in fact the latest migration when Step 1 ran — confirm it matches before proceeding; if `makemigrations` picked a different prior migration as the latest, leave its auto-generated `dependencies` value as-is.)

- [ ] **Step 5: Run the test to verify it passes**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.TournamentCreatePermissionMigrationTests -v 2`
Expected: `OK` (3 tests)

- [ ] **Step 6: Apply the migration locally and run the full suite**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py migrate`
Expected: `Applying federation.0078_grant_tournament_creation_permission... OK` (or the actual generated number). Since the local dev database (seeded from `db.json`) likely doesn't contain users with ids `1`, `65`, `84`, `1084`, or `1839` matching those exact usernames, expect some `WARNING: no user with id=...` lines printed — that's correct, expected behavior, not a failure.

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py check && docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation`
Expected: `OK`, no failures anywhere in the app.

- [ ] **Step 7: Commit**

```bash
git add components/web-api/application/federation/migrations/ \
        components/web-api/application/federation/tests.py
git commit -m "feat(admin): grant add_tournament permission to previously-allowlisted users"
```

---

## After all tasks

Follow `superpowers:finishing-a-development-branch` to decide how to integrate this work. Note for the PR/deploy: once this merges and deploys to production, the data migration in Task 2 runs automatically as part of the existing CI/CD deploy flow (`manage.py migrate` runs on every deploy per `CLAUDE.md`) — no manual production step needed to preserve access for the 5 previously-allowlisted users. Check the deploy logs for any `WARNING:` lines from the migration, which would indicate one of those 5 users' `id`/`username` pairing no longer matches on production (as flagged as a risk during the original bug report in this conversation) and needs manual follow-up via the admin panel.
