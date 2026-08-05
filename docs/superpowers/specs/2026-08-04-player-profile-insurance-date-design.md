# Player Profile Self-Service Insurance Date — Design

## Problem

`Player.insurance_expiration_date` (`federation/models/player.py:73`) exists and drives
`has_valid_insurance()`, which in turn feeds an advisory "insurance missing/expired" warning
shown to tournament organizers (`_can_view_insurance_warnings` in
`federation/views/tournaments.py`) — it is not a hard registration gate.

Today the field is only editable through Django admin (`PlayerAdmin` in
`federation/models/team.py`, unrestricted since `148246c refactor(admin): drop superuser-only
restriction on insurance date`). The self-service profile page
(`federation/views/profile.py` + `federation/forms/player_form.py`) has no insurance field at
all, so players must ask an admin to update it whenever they renew their insurance.

## Scope

In scope: adding `insurance_expiration_date` as a self-editable field on the player's own
profile page (`/profile/`), with a status indicator.

Out of scope: the public player detail page (`players/player.html`, which does not currently
display insurance status — it was removed in an earlier redesign), tournament-side insurance
UI (icons/warnings — already implemented and unaffected), and any change to
`has_valid_insurance()` semantics or its use as an advisory-only signal.

## Requirements (confirmed with stakeholder)

- No date validation beyond "is a valid date" — past dates and dates arbitrarily far in the
  future are both accepted, same as admin can already enter today. No new `clean_*` validator.
- The field gets its own visually distinct row/section within the existing **Profile** tab
  (not a separate tab, not a separate form submission) — a small "Insurance" sub-section
  alongside a status badge (valid-until / expired / none), separate from the personal-info
  fields (name, club, socials) above it.
- The field can be cleared back to blank by the player, same as admin can do today — it does
  not become required once set.

## Approach

Two approaches were considered:

- **Chosen: extend the existing `PlayerForm`/single save.** Add
  `insurance_expiration_date` to `PlayerForm.Meta.fields`. It's saved by the same "Save"
  button that already handles name/club/socials, through the same `profile()` view code path.
- **Rejected: separate mini-form with its own Save button** (mirroring how
  `AuthorizationProfileForm` is a second form for the password tab). Rejected because nothing
  on `PlayerForm` today has cross-field validation that would make errors on one field block
  saving another — the isolation this buys doesn't justify a second form class, a second POST
  branch in `views/profile.py`, and a second audit call for a field with no interaction risk.

Reusing the single form also means insurance-date changes ride the existing
`record_player_change()` audit call in `views/profile.py` for free (see below), rather than
needing a second audit call site.

## Design

### 1. Form field (`federation/forms/player_form.py`)

Add `insurance_expiration_date` to `PlayerForm.Meta.fields`. Declare it explicitly as
`required=False` (Django would infer this from `blank=True` on the model field, but making it
explicit documents the "clearing is allowed" requirement). Label reuses the existing
translated string from the model (`_('Insurance valid until')`, already in
`locale/*/LC_MESSAGES/django.po` from `federation/models/player.py:73`), so no new label
string/translation is needed.

### 2. Layout and status badge (`player_form.py` crispy layout + new template partial)

Add a new `Div` to the crispy `Layout`, placed after the existing rows (socials), containing:

- The `insurance_expiration_date` field itself.
- A small status indicator rendered via a `HTML()` snippet that includes a new partial
  template `forms/profile/insurance_status.html` (same pattern as the existing
  `forms/profile/image_field.html` used for `avatar`), passed `player` as context. The
  partial renders, based on `player.has_valid_insurance()` and
  `player.insurance_expiration_date`:
  - Green: "Valid until {date}" — when a date is set and in the future/today.
  - Red: "Expired {date}" — when a date is set and in the past.
  - Muted: "No insurance on file" — when the field is blank.

  `{date}` is rendered with Django's `|date:"d.m.Y"` template filter, matching the `dd.mm.yyyy`
  convention already used for `birth_date` elsewhere in the profile form.

The status badge reflects the value currently saved on `player` (i.e., updates after a
successful save/reload, not live as the player types).

### 3. Audit trail (`federation/audit/constants.py`)

Add `PLAYER_CHANGE_FIELD_INSURANCE_EXPIRATION_DATE = 'insurance_expiration_date'` and include
it in the `PLAYER_CHANGE_FIELDS` tuple. `views/profile.py` already calls
`record_player_change(request.user, player_before, player)` unconditionally on every profile
save, and `capture_player_change_values()` diffs every field listed in `PLAYER_CHANGE_FIELDS`
— so registering the field is the only change needed for self-service edits to appear in the
audit log (`federation/audit/log_entries.py`, `federation/audit/players.py`). This also makes
"insurance date" a filterable field in the admin audit log UI
(`get_player_change_filter_choices()`), letting staff distinguish player self-edits from admin
edits after the fact.

### 4. View wiring (`federation/views/profile.py`)

No changes. `profile()` already does
`PlayerForm(request.POST, request.FILES, instance=player)` →
`profile_form.save(commit=False)` → `player.save()` →
`record_player_change(request.user, player_before, player)` generically for every field on the
form.

No migration needed — `insurance_expiration_date` already exists on `Player`.

### 5. Testing (`federation/tests.py`, `federation/test_audit.py`)

- `federation/tests.py`: extend the existing profile-update test coverage with cases for
  posting a new `insurance_expiration_date` (past and future dates, both accepted), and
  clearing an existing value back to blank.
- `federation/test_audit.py`: a case confirming a self-service insurance-date change produces
  a `LogEntry` with `insurance_expiration_date` in its changed fields, following the existing
  pattern used for other `PlayerForm` fields.

### 6. Translations

New status-badge strings ("Valid until", "Expired", "No insurance on file" — each wrapped with
`{% trans %}` in the partial template, with the formatted date interpolated separately) are
new strings needing entries in both
`locale/uk/LC_MESSAGES/django.po` and `locale/en/LC_MESSAGES/django.po`, followed by
`compilemessages` to regenerate the corresponding `.mo` files (both `.po` and `.mo` are
committed together, matching the existing convention from commit `466a789`). The field label
itself needs no new translation (reused from the model, see Design §1).

## Non-goals / explicitly out of scope

- No change to whether insurance is a hard gate anywhere — it remains advisory-only.
- No document upload / proof-of-insurance attachment — just the date field.
- No live-as-you-type badge update; badge reflects the persisted value after save.
- No change to the public player detail page.

## Post-merge revision (superseded)

After this design shipped (PR #15), the direction changed: self-service editing was reverted.
`insurance_expiration_date` is admin-only again — removed from `PlayerForm` entirely, same
treatment as `licence_number`/`is_licence_active`. The status badge (§2) is the only surviving
piece of this design; it's kept and now sits directly under the avatar rather than beside an
editable input, since there's no longer an adjacent field for it to label. Design §1 (form
field) and most of §3–§6 (audit registration for self-service edits, translations tied to the
editable-field flow) as originally written describe capability that no longer exists on the
profile page — the audit-trail registration itself is kept, but only serves admin-side edits
now. See PR #17 for the reverting change.
