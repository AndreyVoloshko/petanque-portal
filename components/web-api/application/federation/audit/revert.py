"""Validate and apply safe reversals of enriched audit log entries."""

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .constants import (
    AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY,
    AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY,
    AUDIT_NON_REVERTABLE_FIELDS,
    TOURNAMENT_CHANGE_FIELD_TEAM_PLACES,
)
from .log_entries import log_model_change, log_player_change
from .messages import extract_changed_field_values, extract_changed_fields
from .meta import (
    get_club_model,
    get_document_model,
    get_player_model,
    get_team_tournament_membership_model,
    get_tournament_model,
)
from .model_helpers import get_log_entry_object
from .players import normalize_player_change_fields
from .values import (
    apply_model_field_value,
    build_revert_field_values,
    serialize_model_field_value,
    snapshot_tournament_team_places,
)


def _normalize_log_entry_changed_fields(model, change_message):
    changed_fields = extract_changed_fields(change_message)
    if model == get_player_model():
        return normalize_player_change_fields(changed_fields)

    return changed_fields


def _get_log_entry_revert_reason(log_entry, obj):
    if not log_entry or not log_entry.is_change():
        return _('This action is available only for change entries.')

    model = log_entry.content_type.model_class()
    if model not in {get_player_model(), get_document_model(), get_tournament_model(), get_club_model()}:
        return _('This change cannot be reverted from the log.')

    changed_fields = _normalize_log_entry_changed_fields(model, log_entry.change_message)
    field_values = extract_changed_field_values(log_entry.change_message)
    if not changed_fields or not field_values:
        return _('This log entry does not contain enough data to revert the change.')

    if any(field_name in AUDIT_NON_REVERTABLE_FIELDS for field_name in changed_fields):
        return _('This change cannot be reverted from the log.')

    if any(field_name not in field_values for field_name in changed_fields):
        return _('This log entry does not contain enough data to revert the change.')

    if obj is None:
        return _('The object no longer exists.')

    # Refuse stale reverts so an older log entry cannot overwrite a newer
    # change to any of the same recorded fields.
    if not _values_match(model, obj, field_values):
        return _('The object has changed since this log entry was created. Revert the latest related change first.')

    return ''


def get_log_entry_revert_reason(log_entry):
    """Return an explanation when a log entry cannot be safely reverted."""
    obj = get_log_entry_object(log_entry) if log_entry and log_entry.is_change() else None
    return _get_log_entry_revert_reason(log_entry, obj)


def _values_match(model, obj, field_values):
    if model == get_player_model():
        return _player_values_match(obj, field_values)

    if model == get_tournament_model():
        return _tournament_values_match(obj, field_values)

    return _model_values_match(obj, field_values)


def _model_values_match(instance, field_values):
    for field_name, values in field_values.items():
        current_value = serialize_model_field_value(instance, field_name)
        if current_value != values.get(AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY):
            return False

    return True


def _player_values_match(player, field_values):
    for field_name, values in field_values.items():
        if field_name == 'email':
            current_value = serialize_model_field_value(player.user, 'email')
        else:
            current_value = serialize_model_field_value(player, field_name)

        if current_value != values.get(AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY):
            return False

    return True


def _tournament_values_match(tournament, field_values):
    for field_name, values in field_values.items():
        if field_name == TOURNAMENT_CHANGE_FIELD_TEAM_PLACES:
            membership_ids = [item['membership_id'] for item in values.get(AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY, [])]
            memberships = list(
                get_team_tournament_membership_model().objects
                .filter(tournament=tournament, pk__in=membership_ids)
            )
            if snapshot_tournament_team_places(memberships) != values.get(AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY):
                return False
            continue

        current_value = serialize_model_field_value(tournament, field_name)
        if current_value != values.get(AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY):
            return False

    return True


def revert_log_entry(log_entry, acting_user):
    """Restore recorded old values and create a linked revert log entry."""
    with transaction.atomic():
        locked_log_entry = (
            log_entry.__class__.objects
            .select_for_update()
            .filter(pk=log_entry.pk)
            .first()
        )
        field_values = extract_changed_field_values(locked_log_entry.change_message) if locked_log_entry else {}
        obj = _get_locked_log_entry_object(locked_log_entry, field_values)
        revert_reason = _get_log_entry_revert_reason(locked_log_entry, obj)
        if revert_reason:
            raise ValueError(str(revert_reason))

        model = locked_log_entry.content_type.model_class()
        changed_fields = _normalize_log_entry_changed_fields(model, locked_log_entry.change_message)
        revert_field_values = build_revert_field_values(field_values)
        _apply_revert_values(model, obj, field_values)
        return _log_revert_change(
            model,
            acting_user,
            obj,
            changed_fields,
            revert_field_values,
            locked_log_entry.pk,
        )


def _get_locked_log_entry_object(log_entry, field_values):
    """Lock the target rows that validation and revert will read or update."""
    if not log_entry or not log_entry.object_id:
        return None

    model = log_entry.content_type.model_class()
    if model is None:
        return None

    queryset = model.objects.select_for_update()
    if model == get_player_model():
        obj = queryset.select_related('user').filter(pk=log_entry.object_id).first()
        if obj is not None:
            obj.user = obj.user.__class__.objects.select_for_update().get(pk=obj.user_id)
        return obj

    obj = queryset.filter(pk=log_entry.object_id).first()
    if model == get_tournament_model() and obj is not None:
        team_places = field_values.get(TOURNAMENT_CHANGE_FIELD_TEAM_PLACES, {})
        membership_ids = [
            item['membership_id']
            for item in team_places.get(AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY, [])
        ]
        list(
            get_team_tournament_membership_model().objects
            .select_for_update()
            .filter(tournament=obj, pk__in=membership_ids)
        )

    return obj


def _apply_revert_values(model, obj, field_values):
    if model == get_player_model():
        for field_name, values in field_values.items():
            if field_name == 'email':
                apply_model_field_value(obj.user, 'email', values.get(AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY))
            else:
                apply_model_field_value(obj, field_name, values.get(AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY))

        obj.user.save()
        obj.save()
        return

    if model == get_tournament_model():
        for field_name, values in field_values.items():
            if field_name == TOURNAMENT_CHANGE_FIELD_TEAM_PLACES:
                _apply_tournament_team_places(obj, values.get(AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY, []))
            else:
                apply_model_field_value(obj, field_name, values.get(AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY))

        obj.save()
        return

    for field_name, values in field_values.items():
        apply_model_field_value(obj, field_name, values.get(AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY))

    obj.save()


def _log_revert_change(model, acting_user, obj, changed_fields, revert_field_values, source_log_entry_id):
    if model == get_player_model():
        return log_player_change(
            acting_user,
            obj,
            changed_fields,
            field_values=revert_field_values,
            revert_source_log_entry_id=source_log_entry_id,
        )

    return log_model_change(
        acting_user,
        obj,
        changed_fields,
        field_values=revert_field_values,
        revert_source_log_entry_id=source_log_entry_id,
    )


def _apply_tournament_team_places(tournament, snapshot):
    """Restore place values for the memberships recorded in a snapshot."""
    memberships = {
        membership.pk: membership
        for membership in get_team_tournament_membership_model().objects.filter(
            tournament=tournament,
            pk__in=[item['membership_id'] for item in snapshot],
        )
    }
    for item in snapshot:
        membership = memberships[item['membership_id']]
        membership.place_min = item['place_min']
        membership.place_max = item['place_max']
        membership.save()
