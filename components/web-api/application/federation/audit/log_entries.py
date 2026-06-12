"""Create enriched Django LogEntry records for non-admin mutations."""

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model

from .messages import build_change_message
from .players import normalize_player_change_fields


def get_or_create_system_audit_user(username):
    """Return an inactive, unusable-password user for system-owned changes."""
    user_model = get_user_model()
    user, created = user_model.objects.get_or_create(
        username=username,
        defaults={
            'email': '',
            'is_active': False,
            'is_staff': False,
            'is_superuser': False,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])

    return user


def _create_log_entry(user, obj, change_message):
    """Create a change entry only when it has an authenticated owner."""
    if not change_message or not user or not user.is_authenticated:
        return None

    return LogEntry.objects.log_actions(
        user_id=user.pk,
        queryset=[obj],
        action_flag=CHANGE,
        change_message=change_message,
        single_object=True,
    )


def log_model_change(user, obj, changed_fields, *, field_values=None, revert_source_log_entry_id=None):
    """Log a generic model change using stable field identifiers."""
    return _create_log_entry(
        user,
        obj,
        build_change_message(
            changed_fields,
            field_values=field_values,
            revert_source_log_entry_id=revert_source_log_entry_id,
        ),
    )


def log_player_change(user, player, changed_fields, *, field_values=None, revert_source_log_entry_id=None):
    """Log a player change after applying player-specific normalization."""
    return _create_log_entry(
        user,
        player,
        build_change_message(
            changed_fields,
            field_values=field_values,
            field_normalizer=normalize_player_change_fields,
            revert_source_log_entry_id=revert_source_log_entry_id,
        ),
    )
