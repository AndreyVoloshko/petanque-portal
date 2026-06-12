# Audit Log And Reverting Changes

The application uses Django's built-in `admin.LogEntry` model as a shared
administrative journal for selected player, document, and tournament changes.
No separate audit-history table is introduced.

**Admin route:** `/admin/admin/logentry/`

Primary code:

- Journal admin: `federation/player_change_log_admin.py`
- Audit package: `federation/audit/`
- Admin change capture: `federation/audit_admin.py`
- Revert button template:
  `federation/templates/admin/audit_log/change_form.html`

## Journal Contents

The journal only displays entries whose content type is one of:

- `Player`
- `Document`
- `Tournament`

Django admin create, change, and delete entries for these models are visible.
The additional audit code enriches supported **change** entries with stable
field names and old/new values so selected changes can be reverted.

The list page shows:

- action time
- user that performed the action
- content type
- affected object
- action
- changed fields

Available controls include date hierarchy, search, and filters for content
type, changed field, changed user, action, and action time. Changed-field
choices depend on the selected content type. When no content type is selected,
the changed-field filter shows player fields.

## Logged Change Sources

| Source | Logged behavior | Journal user |
| --- | --- | --- |
| Player edits in Django admin | Supported player form fields | Acting admin |
| Player profile page | Profile fields changed by the player | Acting player |
| Profile password change | Records that password changed; never stores password values | Acting player |
| Player license admin actions | License status and/or license number | Acting admin |
| Document edits in Django admin | Changed document admin fields | Acting admin |
| Tournament edits in Django admin | Changed tournament admin fields | Acting admin |
| Tournament detail page | `meta`, final notes, and team places submitted by an authenticated user | Acting user |
| `POST /api/tournament/results/` | Team result places | `system.tournament.results` |

Player rating and power fields calculated automatically by the application are
intentionally excluded from the player changed-field filter and from enriched
player change logs:

- current regular, B, inclusive, and League rating
- contributing tournament ID collections
- current regular, B, and inclusive power

This prevents scheduled or manual rating recalculation from filling the journal
with derived-data changes.

The existing tournament `meta` mutation can be submitted anonymously. Anonymous
changes are not added to `LogEntry`, because Django audit entries require an
authenticated user. This is part of the existing security-sensitive `meta`
behavior, not an anonymous audit identity.

## Stored Change Message

New revertable entries extend Django's normal `change_message` JSON with stable
field keys and value snapshots:

```json
[
  {
    "changed": {
      "fields": ["current_club"],
      "values": {
        "current_club": {
          "old": 3,
          "new": 7
        }
      }
    }
  }
]
```

Foreign-key values are stored as object IDs. Files are stored as storage names,
not file contents. Tournament team places use a snapshot of the affected
`TeamTournamentMembership` rows.

Older Django log entries may contain translated display labels instead of
stable field keys. The journal normalizes known legacy labels for display and
filtering, but old entries without value snapshots cannot be reverted.

## Reverting A Change

Open a journal entry and use **Revert change**. A revert:

1. verifies that the entry and current object are eligible
2. verifies that the affected fields still match the entry's recorded new
   values
3. restores the recorded old values inside a database transaction
4. preserves the original journal entry
5. creates a new journal entry marked as a revert and linked to the source
   entry

The latest related change must be reverted first. This prevents an older entry
from overwriting newer edits to the same recorded fields.

The user performing the revert must have change permission for the affected
object. Reverting a player email also requires change permission for the linked
Django user.

## Revert Limitations

A journal entry cannot be reverted when:

- it is not a change action, including create and delete entries
- its model is not `Player`, `Document`, or `Tournament`
- it is an old entry without stored old/new values
- the target object no longer exists
- a recorded field no longer matches the entry's new value
- it changes a player's password or linked Django user
- the acting user lacks permission to change the target object

Password changes are logged only as an event. Password values are never stored
and password changes cannot be reverted from the journal.

Reverting file fields restores the stored file name reference. It does not
restore a file that has been removed from the configured storage backend.

## Extending Audit Coverage

For a normal Django admin model change, add
`RevertibleAuditAdminMixin` before `admin.ModelAdmin`. The mixin captures the
object before saving and enriches Django's generated change message afterward.

Mutations outside Django admin must explicitly:

1. load the object state before mutation
2. apply and save the mutation
3. call `record_model_change()` or `record_player_change()` with the acting
   user, before state, and after state

The recording helper owns field selection. Generic model audits compare
concrete editable fields. Player audits use a dedicated allowlist because
player email belongs to the related Django user, password values must never be
stored, and derived rating/power fields must be excluded. Tournament team-place
updates use `record_tournament_team_places_change()` because they compare
membership collections rather than two model instances.

The lower-level `log_model_change()` and `log_player_change()` helpers are
reserved for event-only entries, such as password changes, and audit internals,
such as recording a revert.

Recording helpers intentionally do not load the before state or open a
transaction. The calling use case owns locking and transaction boundaries so
the business mutation and its audit entry can commit or roll back together.

When adding a new revertable model, update the audited-model allowlist in
`player_change_log_admin.py` and the supported-model checks and application
logic in `federation/audit/revert.py`.

## Verification

Focused tests are in:

- `federation.test_audit.PlayerProfileAuditLogTests`
- `federation.test_audit.AuditLogRevertTests`

Run them inside the existing web container:

```bash
docker exec petanque-portal-petanque_portal_web_api-1 \
  python manage.py test \
  federation.test_audit.PlayerProfileAuditLogTests \
  federation.test_audit.AuditLogRevertTests \
  --keepdb --verbosity 1
```
