"""Model-aware labels, filters, normalization, and LogEntry object lookup."""

import json
from functools import lru_cache

from django.conf import settings
from django.utils.translation import gettext_lazy as _, override

from .constants import PLAYER_CHANGE_FIELDS, TOURNAMENT_CHANGE_FIELD_TEAM_PLACES
from .messages import extract_changed_fields
from .meta import get_model_field_label, get_player_model, get_tournament_model
from .players import (
    get_player_change_field_label,
    get_player_change_filter_choices,
    get_player_change_filter_lookup_terms,
    normalize_player_change_fields,
)


def _configured_language_codes():
    return tuple(language_code for language_code, _language_name in settings.LANGUAGES)


@lru_cache(maxsize=None)
def get_model_change_filter_fields(model):
    """Return fields that may appear in the changed-field admin filter."""
    if model == get_player_model():
        return PLAYER_CHANGE_FIELDS

    filter_fields = tuple(
        field.name
        for field in model._meta.fields
        if not field.auto_created and not field.primary_key and getattr(field, 'editable', True)
    )
    if model == get_tournament_model():
        return filter_fields + (TOURNAMENT_CHANGE_FIELD_TEAM_PLACES,)

    return filter_fields


def get_model_change_field_label(model, field_name):
    """Return the current-language display label for an audited field."""
    if model == get_player_model():
        return get_player_change_field_label(field_name)

    if model == get_tournament_model() and field_name == TOURNAMENT_CHANGE_FIELD_TEAM_PLACES:
        return _('Team places')

    return get_model_field_label(model, field_name) or field_name


@lru_cache(maxsize=None)
def _get_model_legacy_lookup_labels(model, field_name):
    labels = set()
    for language_code in _configured_language_codes():
        with override(language_code):
            labels.add(str(get_model_change_field_label(model, field_name)))

    return tuple(label for label in labels if label)


@lru_cache(maxsize=None)
def _get_model_legacy_field_name_map(model):
    field_name_map = {}
    for field_name in get_model_change_filter_fields(model):
        for legacy_label in _get_model_legacy_lookup_labels(model, field_name):
            field_name_map[legacy_label] = field_name

    return field_name_map


def normalize_model_change_fields(model, changed_fields):
    """Normalize current and historical labels to stable model field names."""
    if model == get_player_model():
        return normalize_player_change_fields(changed_fields)

    field_name_map = _get_model_legacy_field_name_map(model)
    normalized_fields = []
    seen_fields = set()

    for field in changed_fields:
        field_name = field_name_map.get(str(field), str(field))
        if not field_name or field_name in seen_fields:
            continue

        normalized_fields.append(field_name)
        seen_fields.add(field_name)

    return normalized_fields


def format_model_change_fields(model, change_message):
    """Format changed fields from a LogEntry for admin display."""
    changed_fields = extract_changed_fields(change_message)
    if model is not None:
        changed_fields = normalize_model_change_fields(model, changed_fields)

    if not changed_fields:
        return ''

    return ', '.join(str(get_model_change_field_label(model, field_name)) for field_name in changed_fields)


def get_model_change_filter_choices(model):
    """Return changed-field filter choices for an audited model."""
    if model == get_player_model():
        return get_player_change_filter_choices()

    return tuple(
        (field_name, get_model_change_field_label(model, field_name))
        for field_name in get_model_change_filter_fields(model)
    )


def get_model_change_filter_lookup_terms(model, filter_key):
    """Return JSON lookup terms that also match historical translated labels."""
    if model == get_player_model():
        return get_player_change_filter_lookup_terms(filter_key)

    if filter_key not in get_model_change_filter_fields(model):
        return ()

    lookup_values = [filter_key, *_get_model_legacy_lookup_labels(model, filter_key)]
    return tuple(json.dumps(str(value)) for value in lookup_values)


def get_log_entry_object(log_entry):
    """Resolve a LogEntry target, loading the related user for players."""
    model = log_entry.content_type.model_class()
    if not model or not log_entry.object_id:
        return None

    if model == get_player_model():
        return model.objects.select_related('user').filter(pk=log_entry.object_id).first()

    return model.objects.filter(pk=log_entry.object_id).first()
