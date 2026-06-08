# Authentication, Registration, And Profile

This area connects Django's built-in `auth_user` model to the domain-specific
`Player` model through a required one-to-one relation.

```text
auth_user 1 <-> 1 federation_player
auth_user 1 <-> 0..1 federation_emailconfirmation
```

Primary code:

- Routes: `components/web-api/application/federation/urls.py`
- Views: `federation/views/register.py`, `login.py`, `logout.py`, `profile.py`,
  `email_confirm.py`, `password_reset.py`
- Forms: `federation/forms/registration_player_form.py`, `player_form.py`,
  `authorization_profile_form.py`
- Models: `federation/models/player.py`, `email_confirmation.py`

## Player Registration

**Route:** `GET/POST /register/player/`
**View:** `views/register.py:register_player`
**Template:** `templates/register/player.html`
**Form:** `forms/registration_player_form.py:RegistrationPlayerForm`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Header | Player-registration title and purpose | `templates/register/player.html` registration header |
| Identity fields | Surname, name, patronymic | template field grid; `RegistrationPlayerForm.__init__` |
| Birth-date picker | Custom client-side calendar, accepts `dd.mm.yyyy` or ISO, blocks future dates | template inline JavaScript; `RegistrationPlayerForm.clean_birth_date` |
| Country/gender/license | Required country and gender; optional existing federation license | form initialization; `Player` fields |
| Account access | Email/password/password confirmation shown only for Ukraine; optional until email is entered | template `account-access-field-group`; `RegistrationPlayerForm.clean` |
| Submit and automatic bot check | Loads Google reCAPTCHA when configured and submits a hidden token | template inline JavaScript; `utils/autocaptcha.py` |
| Duplicate warning/search | Public player search before registration, with links to existing profiles | template registration sidebar; `views/api.py:players_list` |
| Error/success messages | Non-field and field errors plus Django messages | template; `views/register.py:register_player` |

### Validation And Persistence

`RegistrationPlayerForm.clean()`:

- Rejects a matching first-name/surname player using
  `Player.get_by_name_and_surname`.
- Clears patronymic and all account credentials for non-Ukrainian players.
- Requires password and confirmation when an email is supplied.
- Rejects duplicate emails and applies Django password validators.
- Validates the automatic CAPTCHA after all local validation passes.

On success, `register_player` runs in a database transaction:

1. Generates a unique transliterated username with
   `views/register.py:generate_username`.
2. Creates `auth_user`.
3. Creates `federation_player`.
4. Creates `EmailConfirmation` and sends mail when email was supplied.
5. Logs the user in and redirects to `/profile/`.

The entered license number does not activate the license. License activation is
an admin operation in `admin_actions/player.py`.

## Team Registration

**Route:** `GET/POST /register/team/<tournament_id>/`
**View:** `views/register.py:register_team`
**Template:** `templates/register/team.html`
**Form:** `forms/registration_team_form.py:RegistrationTeamForm`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Team form | Dynamic required/reserve player selectors based on tournament min/max size | `RegistrationTeamForm.__init__` |
| Player autocomplete | Select2 calls `/api/players_list/list/` | template inline JavaScript; `views/api.py:players_list` |
| Registration status | Hides form and shows closed message when deadline has passed | `Tournament.is_registration_opened`; template |
| Tournament summary | Reuses tournament summary partial | `templates/tournaments/tournament_summary.html` |
| Missing-player help | Links to player registration and warns against duplicates | template |

On success the flow calls `Team.get_or_create_for_players()`, creates a
`TeamTournamentMembership` through `Tournament.add_team()`, recalculates the
tournament's provisional power, and redirects to tournament detail.

The route is public. A player cannot be added twice to the same tournament
because the form checks `Tournament.get_team_which_contains_player()`.

## Login And Logout

### Login

**Route:** `GET/POST /login/`
**View:** `views/login.py:application_login`
**Template:** `templates/login.html`

| Block | Behavior | Code references |
| --- | --- | --- |
| Username/email field | First authenticates as username; then resolves email to username and retries | `application_login` |
| Password field | Uses Django authentication backend | `application_login` |
| Safe next redirect | Accepts same-host `next`, otherwise `/profile/` | `views/login.py:_safe_next_url` |
| Password reset link | Starts reset flow | template and password-reset routes |
| Registration link | Opens player registration | template |

Authenticated visitors are redirected to `/profile/`. After successful login,
users with a pending `EmailConfirmation` are redirected to `/email/prompt/`.
Legacy users with an email and no confirmation row are marked confirmed by
`_sync_existing_email_confirmation`.

### Logout

**Route:** `GET /logout/`
**View:** `views/logout.py:application_logout`

The view calls Django `logout()` and redirects to `/`.

## Email Confirmation

| Route | Page/behavior | Code references |
| --- | --- | --- |
| `/email/prompt/` | Enter/resend email, show pending state, allow skip to safe next URL | `views/email_confirm.py:email_prompt`; `templates/email_confirm/prompt.html` |
| `/email/confirm/<token>/` | Validate unconfirmed token, 24-hour expiry, and email uniqueness; copy email to `auth_user` | `email_confirm`; `models/email_confirmation.py`; success/invalid templates |

Sending uses `utils/email.py:send_confirmation_email` and
`templates/email_confirm/email_subject.txt` / `email_body.html`.

## Password Reset

| Route | Block | Code references |
| --- | --- | --- |
| `/password-reset/` | Email request form and explicit "not found" state | `CustomPasswordResetView`; `ConfirmedPasswordResetForm`; `templates/password_reset/request.html` |
| `/password-reset/done/` | Email-sent confirmation | Django `PasswordResetDoneView`; `done.html` |
| `/password-reset/<uidb64>/<token>/` | New password fields | `CustomPasswordResetConfirmView`; `StyledSetPasswordForm`; `confirm.html` |
| `/password-reset/complete/` | Completion page | Django `PasswordResetCompleteView`; `complete.html` |

`ConfirmedPasswordResetForm.get_users()` permits active users with usable
passwords when their email confirmation is confirmed, or when they are legacy
users with no `EmailConfirmation` row.

## User Profile

**Route:** `GET/POST /profile/`, login required
**View:** `views/profile.py:profile`
**Template:** `templates/profile.html`

### Page Blocks

| Block | Behavior/data | Code references |
| --- | --- | --- |
| Profile tab | Avatar, identity, email, demographics, current club, country, social links, preferred position | `forms/player_form.py:PlayerForm`; custom avatar template `templates/forms/profile/image_field.html` |
| Authorization tab | Read-only username, current password, new password, confirmation | `forms/authorization_profile_form.py:AuthorizationProfileForm` |
| Flash messages | Profile updated/password changed | `views/profile.py:profile`; `templates/common/messages.html` |

POST dispatch is inferred from submitted field names:

- A POST containing `name` is treated as a profile update.
- A POST containing `old_password` is treated as a password change.

`PlayerForm.save()` also writes the email to the related `auth_user`. It does
not create or reset an `EmailConfirmation` row, so email-confirmation semantics
after profile email changes should be reviewed before changing that flow.

## Public Player Profile Versus Editable Profile

Do not confuse:

- `/profile/`: editable account page for the logged-in user.
- `/player/<id>`: public player detail and rating history.

The public page is documented in [Home, players, and ratings](home-players-ratings.md).

## Data And Security Notes

- `Player.user` is required and unique. Deleting the user cascades to Player.
- `EmailConfirmation.user` is required and unique. Deleting the user cascades
  to the confirmation.
- Email uniqueness is enforced in forms/views, not by a database unique
  constraint on `auth_user.email`.
- Team registration and player-search APIs are public.
- Player registration can create users without usable passwords when no email
  is supplied.
