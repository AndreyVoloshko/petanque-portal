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
        ('federation', '0078_organizertournamentmembership'),
    ]

    operations = [
        migrations.RunPython(grant_add_tournament_permission, migrations.RunPython.noop),
    ]
