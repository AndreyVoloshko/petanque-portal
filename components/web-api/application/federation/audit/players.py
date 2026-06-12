"""Player-specific audit labels, filtering, normalization, and snapshots."""

import json
from functools import lru_cache

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _, override

from .constants import (
    AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY,
    AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY,
    PLAYER_CHANGE_FIELDS,
    PLAYER_CHANGE_FIELD_PASSWORD,
    PLAYER_CHANGE_FILTER_ALIASES,
    PLAYER_CHANGE_IGNORED_FIELDS,
)
from .messages import extract_changed_fields
from .meta import get_model_field_label, get_player_model
from .values import serialize_model_field_value


@lru_cache(maxsize=1)
def get_profile_form_labels():
    from federation.forms.player_form import PlayerForm
    return {
        field_name: field.label
        for field_name, field in PlayerForm.base_fields.items()
        if field.label
    }


def get_user_model_field_label(field_name):
    return get_model_field_label(get_user_model(), field_name)


def get_player_model_field_label(field_name):
    return get_model_field_label(get_player_model(), field_name)


def get_player_change_field_label(field_name):
    """Return the best current-language label for a player audit field."""
    profile_form_label = get_profile_form_labels().get(field_name)
    if profile_form_label:
        return profile_form_label

    if field_name == 'user':
        return _('User')

    if field_name in ('email', PLAYER_CHANGE_FIELD_PASSWORD):
        return get_user_model_field_label(field_name) or field_name

    return get_player_model_field_label(field_name) or field_name


def _get_player_field_labels(field_name):
    labels = {str(get_player_change_field_label(field_name))}

    if field_name in ('email', PLAYER_CHANGE_FIELD_PASSWORD):
        model_label = get_user_model_field_label(field_name)
    else:
        model_label = get_player_model_field_label(field_name)
    if model_label:
        labels.add(str(model_label))

    profile_form_label = get_profile_form_labels().get(field_name)
    if profile_form_label:
        labels.add(str(profile_form_label))

    return labels


def _configured_language_codes():
    return tuple(language_code for language_code, _language_name in settings.LANGUAGES)


@lru_cache(maxsize=1)
def _get_player_legacy_field_name_map():
    """Map historical translated labels back to stable player field names."""
    field_name_map = {}
    for language_code in _configured_language_codes():
        with override(language_code):
            for field_name in PLAYER_CHANGE_FIELDS:
                for label in _get_player_field_labels(field_name):
                    field_name_map[label] = field_name

    return field_name_map


def normalize_player_change_fields(changed_fields):
    """Normalize legacy labels and remove derived player fields from audit."""
    normalized_fields = []
    seen_fields = set()

    for field in changed_fields:
        if not field:
            continue

        field_name = _get_player_legacy_field_name_map().get(str(field), str(field))
        if field_name in PLAYER_CHANGE_IGNORED_FIELDS or field_name in seen_fields:
            continue

        normalized_fields.append(field_name)
        seen_fields.add(field_name)

    return normalized_fields


@lru_cache(maxsize=1)
def _get_player_change_field_by_filter():
    return {
        PLAYER_CHANGE_FILTER_ALIASES.get(field_name, field_name): field_name
        for field_name in PLAYER_CHANGE_FIELDS
    }


def get_player_change_filter_choices():
    """Return stable filter keys with current-language player field labels."""
    return tuple(
        (
            PLAYER_CHANGE_FILTER_ALIASES.get(field_name, field_name),
            get_player_change_field_label(field_name),
        )
        for field_name in PLAYER_CHANGE_FIELDS
    )


def _get_player_legacy_lookup_labels(field_name):
    return tuple(
        legacy_label
        for legacy_label, mapped_field_name in _get_player_legacy_field_name_map().items()
        if mapped_field_name == field_name
    )


def get_player_change_filter_lookup_terms(filter_key):
    """Return JSON lookup terms covering stable and historical field labels."""
    field_name = _get_player_change_field_by_filter().get(filter_key)
    if not field_name:
        return ()

    lookup_values = [field_name, *_get_player_legacy_lookup_labels(field_name)]
    return tuple(json.dumps(str(value)) for value in lookup_values)


def capture_player_change_values(before_player, after_player, changed_fields=None):
    """Apply player audit policy and capture revertable old/new values."""
    if changed_fields is None:
        changed_fields = PLAYER_CHANGE_FIELDS

    field_values = {}
    for field_name in normalize_player_change_fields(changed_fields):
        # Password events are auditable, but password values must never enter
        # LogEntry change messages.
        if field_name == PLAYER_CHANGE_FIELD_PASSWORD:
            continue

        if field_name == 'email':
            old_value = serialize_model_field_value(before_player.user, 'email')
            new_value = serialize_model_field_value(after_player.user, 'email')
        else:
            old_value = serialize_model_field_value(before_player, field_name)
            new_value = serialize_model_field_value(after_player, field_name)
        if old_value == new_value:
            continue

        field_values[field_name] = {
            AUDIT_CHANGE_MESSAGE_OLD_VALUE_KEY: old_value,
            AUDIT_CHANGE_MESSAGE_NEW_VALUE_KEY: new_value,
        }

    return field_values


def format_player_change_fields(change_message):
    """Format player field identifiers using their current-language labels."""
    changed_fields = normalize_player_change_fields(extract_changed_fields(change_message))
    if not changed_fields:
        return ''

    return ', '.join(str(get_player_change_field_label(field_name)) for field_name in changed_fields)
