"""Parse and enrich Django LogEntry change-message JSON."""

import json

from .constants import (
    AUDIT_CHANGE_MESSAGE_REVERTED_KEY,
    AUDIT_CHANGE_MESSAGE_SOURCE_LOG_ENTRY_ID_KEY,
    AUDIT_CHANGE_MESSAGE_VALUES_KEY,
    PLAYER_CHANGE_MESSAGE_CHANGED_KEY,
    PLAYER_CHANGE_MESSAGE_FIELDS_KEY,
)


def deduplicate_fields(changed_fields):
    unique_fields = []
    seen_fields = set()

    for field_name in changed_fields:
        if not field_name or field_name in seen_fields:
            continue

        unique_fields.append(field_name)
        seen_fields.add(field_name)

    return unique_fields


def normalize_message_fields(changed_fields, field_normalizer=None):
    if field_normalizer is not None:
        return field_normalizer(changed_fields)

    return deduplicate_fields(changed_fields)


def extract_change_entries(change_message):
    """Return parsed change-message entries, accepting stored JSON or a list."""
    if isinstance(change_message, list):
        return change_message

    if not isinstance(change_message, str) or not change_message.startswith('['):
        return []

    try:
        return json.loads(change_message)
    except json.JSONDecodeError:
        return []


def extract_changed_fields(change_message):
    """Return unique field identifiers from all change entries."""
    changed_fields = []
    for message in extract_change_entries(change_message):
        if not isinstance(message, dict):
            continue

        changed = message.get(PLAYER_CHANGE_MESSAGE_CHANGED_KEY)
        if isinstance(changed, dict):
            changed_fields.extend(changed.get(PLAYER_CHANGE_MESSAGE_FIELDS_KEY, []))

    return deduplicate_fields(changed_fields)


def extract_changed_field_values(change_message):
    """Return the old/new value snapshot attached to the main change entry."""
    for message in extract_change_entries(change_message):
        if not isinstance(message, dict):
            continue

        changed = message.get(PLAYER_CHANGE_MESSAGE_CHANGED_KEY)
        if isinstance(changed, dict):
            values = changed.get(AUDIT_CHANGE_MESSAGE_VALUES_KEY)
            if isinstance(values, dict):
                return values

    return {}


def get_revert_source_log_entry_id(change_message):
    """Return the original log-entry ID when this message records a revert."""
    for message in extract_change_entries(change_message):
        if not isinstance(message, dict):
            continue

        reverted = message.get(AUDIT_CHANGE_MESSAGE_REVERTED_KEY)
        if isinstance(reverted, dict):
            return reverted.get(AUDIT_CHANGE_MESSAGE_SOURCE_LOG_ENTRY_ID_KEY)

    return None


def is_revert_change_message(change_message):
    """Return whether a change message was created by a revert."""
    return get_revert_source_log_entry_id(change_message) is not None


def build_change_message(changed_fields, *, field_values=None, field_normalizer=None, revert_source_log_entry_id=None):
    """Build a Django-compatible change message with optional revert metadata."""
    normalized_fields = normalize_message_fields(changed_fields, field_normalizer=field_normalizer)
    if not normalized_fields:
        return []

    changed_message = {
        PLAYER_CHANGE_MESSAGE_FIELDS_KEY: normalized_fields,
    }
    if field_values:
        changed_message[AUDIT_CHANGE_MESSAGE_VALUES_KEY] = field_values

    message = {
        PLAYER_CHANGE_MESSAGE_CHANGED_KEY: changed_message,
    }
    if revert_source_log_entry_id is not None:
        message[AUDIT_CHANGE_MESSAGE_REVERTED_KEY] = {
            AUDIT_CHANGE_MESSAGE_SOURCE_LOG_ENTRY_ID_KEY: revert_source_log_entry_id,
        }

    return [message]


def replace_changed_fields_in_message(change_message, changed_fields, *, field_values=None, field_normalizer=None, revert_source_log_entry_id=None):
    """Enrich the main model change while preserving Django inline entries."""
    normalized_fields = normalize_message_fields(changed_fields, field_normalizer=field_normalizer)

    if not isinstance(change_message, list):
        return change_message

    updated_change_message = []
    replaced_main_change = False

    for message in change_message:
        if not isinstance(message, dict):
            updated_change_message.append(message)
            continue

        changed = message.get(PLAYER_CHANGE_MESSAGE_CHANGED_KEY)
        if not isinstance(changed, dict):
            updated_change_message.append(message)
            continue

        # Django marks inline changes with name/object metadata; those entries
        # must remain intact while the parent model entry gains audit values.
        is_main_change = 'name' not in changed and 'object' not in changed
        if not is_main_change:
            updated_change_message.append(message)
            continue

        replaced_main_change = True
        if not normalized_fields:
            continue

        updated_message = dict(message)
        updated_changed = dict(changed)
        updated_changed[PLAYER_CHANGE_MESSAGE_FIELDS_KEY] = normalized_fields
        if field_values:
            updated_changed[AUDIT_CHANGE_MESSAGE_VALUES_KEY] = field_values
        else:
            updated_changed.pop(AUDIT_CHANGE_MESSAGE_VALUES_KEY, None)

        updated_message[PLAYER_CHANGE_MESSAGE_CHANGED_KEY] = updated_changed
        if revert_source_log_entry_id is not None:
            updated_message[AUDIT_CHANGE_MESSAGE_REVERTED_KEY] = {
                AUDIT_CHANGE_MESSAGE_SOURCE_LOG_ENTRY_ID_KEY: revert_source_log_entry_id,
            }
        else:
            updated_message.pop(AUDIT_CHANGE_MESSAGE_REVERTED_KEY, None)

        updated_change_message.append(updated_message)

    if replaced_main_change:
        return updated_change_message

    if normalized_fields:
        return build_change_message(
            normalized_fields,
            field_values=field_values,
            revert_source_log_entry_id=revert_source_log_entry_id,
        )

    return updated_change_message
