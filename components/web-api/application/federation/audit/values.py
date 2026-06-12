"""Serialize model values into reversible LogEntry snapshots."""

from datetime import date, datetime, time
from decimal import Decimal

from django.db.models import FileField, ForeignKey
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django_countries.fields import Country

from .constants import (
    AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY,
    AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY,
    TOURNAMENT_CHANGE_FIELD_TEAM_PLACES,
)
from .messages import deduplicate_fields


def _serialize_scalar_value(value):
    if isinstance(value, Country):
        return value.code

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (date, datetime, time)):
        return value.isoformat()

    return value


def serialize_model_field_value(instance, field_name):
    """Serialize a model field into a JSON-compatible stable value."""
    field = instance._meta.get_field(field_name)
    if isinstance(field, ForeignKey):
        return getattr(instance, field.attname)

    if isinstance(field, FileField):
        file_value = getattr(instance, field.name)
        return getattr(file_value, 'name', None) or None

    return _serialize_scalar_value(field.value_from_object(instance))


def deserialize_model_field_value(model, field_name, value):
    """Convert a stored audit value back to the model field's Python type."""
    field = model._meta.get_field(field_name)
    if value is None:
        return None

    if isinstance(field, ForeignKey):
        return value

    internal_type = field.get_internal_type()
    if internal_type == 'DecimalField':
        return Decimal(value)
    if internal_type == 'DateField':
        return parse_date(value)
    if internal_type == 'DateTimeField':
        return parse_datetime(value)
    if internal_type == 'TimeField':
        return parse_time(value)

    return field.to_python(value)


def apply_model_field_value(instance, field_name, value):
    """Apply a stored audit value without fetching related objects."""
    field = instance._meta.get_field(field_name)
    converted_value = deserialize_model_field_value(instance.__class__, field_name, value)
    target_name = field.attname if isinstance(field, ForeignKey) else field.name
    setattr(instance, target_name, converted_value)


def capture_model_change_values(before_instance, after_instance, changed_fields):
    """Capture old/new values for generic model fields."""
    field_values = {}
    for field_name in deduplicate_fields(changed_fields):
        old_value = serialize_model_field_value(before_instance, field_name)
        new_value = serialize_model_field_value(after_instance, field_name)
        if old_value == new_value:
            continue

        field_values[field_name] = {
            AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY: old_value,
            AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY: new_value,
        }

    return field_values


def snapshot_tournament_team_places(memberships):
    """Create a deterministic snapshot of tournament membership places."""
    return [
        {
            'membership_id': membership.pk,
            'team_id': membership.team_id,
            'place_min': membership.place_min,
            'place_max': membership.place_max,
        }
        for membership in sorted(memberships, key=lambda item: item.pk)
    ]


def build_tournament_team_places_field_values(before_memberships, after_memberships):
    """Build a revertable team-place value snapshot when places changed."""
    before_snapshot = snapshot_tournament_team_places(before_memberships)
    after_snapshot = snapshot_tournament_team_places(after_memberships)
    if before_snapshot == after_snapshot:
        return {}

    return {
        TOURNAMENT_CHANGE_FIELD_TEAM_PLACES: {
            AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY: before_snapshot,
            AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY: after_snapshot,
        },
    }


def build_revert_field_values(field_values):
    """Swap old/new values for the audit entry produced by a revert."""
    return {
        field_name: {
            AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY: values.get(AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY),
            AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY: values.get(AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY),
        }
        for field_name, values in field_values.items()
    }
