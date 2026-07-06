# Image Upload Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce a max file size, max pixel dimensions, and an allowed-format list on `Player.avatar` and `Club.logo` uploads, identically from both the public profile form and the Django admin, by attaching validators directly to the model fields.

**Architecture:** A new `federation/validators.py` module holds three small, independently testable validator functions (size, dimensions, format) built on Pillow (already a dependency) plus Django's built-in `FileExtensionValidator`. They're attached to the model fields, not the form, so both the profile `PlayerForm` and Django admin's auto-generated `ModelForm`s inherit the same rules for free.

**Tech Stack:** Django 5.1.6, Pillow (already installed, unpinned), no new dependencies.

## Global Constraints

- Max file size: 3 MB (`settings.MAX_UPLOAD_SIZE = 3 * 1024 * 1024`).
- Max pixel dimensions: 4000×4000 px (`settings.MAX_IMAGE_DIMENSION_PX = 4000`).
- Allowed formats: JPEG, PNG, WebP only — no GIF/BMP/TIFF (`settings.ALLOWED_IMAGE_FORMATS = ['JPEG', 'PNG', 'WEBP']`).
- Behavior on violation: reject with a translated `ValidationError` — no auto-resize/re-encode.
- Scope: `Player.avatar` and `Club.logo` only. `Tournament.terms` and `Document.file` are explicitly out of scope.
- No new third-party dependency — Django built-ins + Pillow only.
- User-visible strings must use `gettext`/`_()` (Ukrainian locale project convention).
- `manage.py` commands (tests, migrations) run inside the docker container:
  `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py <command>`.
- Never hand-edit generated migration files' logic — only run `makemigrations` and verify/commit the output.
- Test file is the existing `federation/tests.py` (single file, `TestCase`/`SimpleTestCase` classes) — do not create a new test module; this is the established convention despite CLAUDE.md calling it a placeholder.

---

### Task 1: Settings constants for image validation

**Files:**
- Modify: `components/web-api/application/api/settings.py:169-179`

**Interfaces:**
- Produces: `settings.MAX_UPLOAD_SIZE` (int, bytes), `settings.MAX_IMAGE_DIMENSION_PX` (int), `settings.ALLOWED_IMAGE_FORMATS` (list of str, Pillow format names).

- [ ] **Step 1: Replace the orphaned settings**

Current content at `api/settings.py:169-179`:

```python
CONTENT_TYPES = ['image']

# 2.5MB - 2621440
# 5MB - 5242880
# 10MB - 10485760
# 20MB - 20971520
# 50MB - 5242880
# 100MB 104857600
# 250MB - 214958080
# 500MB - 429916160
MAX_UPLOAD_SIZE = "2621440"
```

Replace with:

```python
# Image upload validation for avatar/logo fields (federation/validators.py).
# Applies to Player.avatar and Club.logo only.
MAX_UPLOAD_SIZE = 3 * 1024 * 1024  # 3 MB
MAX_IMAGE_DIMENSION_PX = 4000  # max width/height in pixels
ALLOWED_IMAGE_FORMATS = ['JPEG', 'PNG', 'WEBP']  # Pillow-detected formats, not file extensions
```

`CONTENT_TYPES` is removed entirely — it was only ever read by the dead `clean_content` method
in `player_form.py` (removed in Task 4), confirmed via
`grep -rn "CONTENT_TYPES\|MAX_UPLOAD_SIZE" --include="*.py" --include="*.html" .` returning no
other usages.

- [ ] **Step 2: Verify Django still boots**

Run: `docker compose -p petanque-portal exec petanque_portal_web_api python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Commit**

```bash
git add components/web-api/application/api/settings.py
git commit -m "fix(settings): replace orphaned upload-size settings with typed image limits"
```

---

### Task 2: Image validators module

**Files:**
- Create: `components/web-api/application/federation/validators.py`
- Test: `components/web-api/application/federation/tests.py` (append new `ImageValidatorsTests` class)

**Interfaces:**
- Consumes: `settings.MAX_UPLOAD_SIZE`, `settings.MAX_IMAGE_DIMENSION_PX`, `settings.ALLOWED_IMAGE_FORMATS` (Task 1).
- Produces: `validate_image_file_size(file)`, `validate_image_dimensions(file)`,
  `validate_image_format(file)` — each takes a Django `UploadedFile`-like object (must support
  `.size`, `.seek()`, and be openable by `PIL.Image.open`) and raises
  `django.core.exceptions.ValidationError` on violation, otherwise returns `None`. These are
  consumed by Task 3.

- [ ] **Step 1: Write the failing tests**

Append to `components/web-api/application/federation/tests.py` (near the existing
`PlayerProfileFormTests` class, ~line 709). Add these imports to the existing import block at
the top of the file:

```python
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from federation.validators import (
    validate_image_dimensions,
    validate_image_file_size,
    validate_image_format,
)
```

Then add the test class:

```python
def _make_uploaded_image(width, height, image_format='JPEG', file_name='test.jpg',
                          content_type='image/jpeg'):
    buffer = BytesIO()
    Image.new('RGB', (width, height), color='red').save(buffer, format=image_format)
    return SimpleUploadedFile(file_name, buffer.getvalue(), content_type=content_type)


class ImageValidatorsTests(SimpleTestCase):
    def test_validate_image_file_size_accepts_file_under_limit(self):
        small_file = SimpleUploadedFile('small.jpg', b'x' * 1024, content_type='image/jpeg')

        self.assertIsNone(validate_image_file_size(small_file))

    def test_validate_image_file_size_rejects_file_over_limit(self):
        oversized_file = SimpleUploadedFile(
            'big.jpg', b'x' * (settings.MAX_UPLOAD_SIZE + 1), content_type='image/jpeg'
        )

        with self.assertRaises(ValidationError):
            validate_image_file_size(oversized_file)

    def test_validate_image_dimensions_accepts_image_within_limit(self):
        image = _make_uploaded_image(100, 100)

        self.assertIsNone(validate_image_dimensions(image))

    def test_validate_image_dimensions_rejects_image_over_limit(self):
        image = _make_uploaded_image(settings.MAX_IMAGE_DIMENSION_PX + 1, 10)

        with self.assertRaises(ValidationError):
            validate_image_dimensions(image)

    def test_validate_image_format_accepts_allowed_formats(self):
        for image_format in ('JPEG', 'PNG', 'WEBP'):
            with self.subTest(image_format=image_format):
                image = _make_uploaded_image(10, 10, image_format=image_format)

                self.assertIsNone(validate_image_format(image))

    def test_validate_image_format_rejects_disallowed_format(self):
        image = _make_uploaded_image(10, 10, image_format='BMP')

        with self.assertRaises(ValidationError):
            validate_image_format(image)

    def test_validate_image_format_rejects_spoofed_extension(self):
        # A file named .jpg whose actual content is a BMP must still be rejected —
        # validate_image_format checks Pillow's detected format, not the filename.
        image = _make_uploaded_image(10, 10, image_format='BMP', file_name='fake.jpg',
                                      content_type='image/jpeg')

        with self.assertRaises(ValidationError):
            validate_image_format(image)
```

Note: `settings` is already imported in `tests.py` via `from django.conf import settings`— check
the existing import block first; if it's not already imported, add
`from django.conf import settings` to the import block above.

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.ImageValidatorsTests -v 2
```
Expected: FAIL with `ModuleNotFoundError: No module named 'federation.validators'`

- [ ] **Step 3: Write the validators module**

Create `components/web-api/application/federation/validators.py`:

```python
from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _
from PIL import Image


def validate_image_file_size(file):
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(
            _('File size must not exceed %(max_size)s. Current file size: %(current_size)s.'),
            params={
                'max_size': filesizeformat(settings.MAX_UPLOAD_SIZE),
                'current_size': filesizeformat(file.size),
            },
        )


def validate_image_dimensions(file):
    file.seek(0)
    with Image.open(file) as image:
        width, height = image.size
    file.seek(0)

    max_dimension = settings.MAX_IMAGE_DIMENSION_PX
    if width > max_dimension or height > max_dimension:
        raise ValidationError(
            _('Image dimensions must not exceed %(max)s×%(max)s px. '
              'Current dimensions: %(width)s×%(height)s px.'),
            params={'max': max_dimension, 'width': width, 'height': height},
        )


def validate_image_format(file):
    file.seek(0)
    with Image.open(file) as image:
        image_format = image.format
    file.seek(0)

    if image_format not in settings.ALLOWED_IMAGE_FORMATS:
        raise ValidationError(
            _('Unsupported image format "%(format)s". Allowed formats: %(allowed)s.'),
            params={
                'format': image_format,
                'allowed': ', '.join(settings.ALLOWED_IMAGE_FORMATS),
            },
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.ImageValidatorsTests -v 2
```
Expected: `OK` with all 7 tests passing.

- [ ] **Step 5: Commit**

```bash
git add components/web-api/application/federation/validators.py components/web-api/application/federation/tests.py
git commit -m "feat(federation): add image upload validators for size, dimensions, format"
```

---

### Task 3: Wire validators onto Player.avatar and Club.logo

**Files:**
- Modify: `components/web-api/application/federation/models/player.py:58`
- Modify: `components/web-api/application/federation/models/club.py:11`
- Create: migration file under `components/web-api/application/federation/migrations/`, auto-generated by `manage.py makemigrations` in Step 4 below (filename decided by Django, not written by hand)
- Test: `components/web-api/application/federation/tests.py` (append new `ImageFieldValidationTests` class)

**Interfaces:**
- Consumes: `validate_image_file_size`, `validate_image_dimensions`, `validate_image_format`
  from `federation/validators.py` (Task 2); Django's built-in
  `django.core.validators.FileExtensionValidator`.
- Produces: `Player.avatar` and `Club.logo` now reject invalid uploads through any `ModelForm`
  built on them (profile form and Django admin both consume this in Task 4/manual verification).

- [ ] **Step 1: Write the failing tests**

Append to `components/web-api/application/federation/tests.py`, after the
`ImageValidatorsTests` class added in Task 2. Add this import to the top import block:

```python
from django import forms as django_forms
```

(Only add it if `forms` isn't already imported under a different alias — check the existing
import block first.)

```python
class ImageFieldValidationTests(TestCase):
    def test_player_form_rejects_oversized_avatar(self):
        user = User.objects.create_user(username='avatar_size_test')
        player = Player.objects.create(
            user=user, name='Test', surname='Player', birth_date=date(1990, 1, 1),
        )
        oversized_file = SimpleUploadedFile(
            'big.jpg', b'x' * (settings.MAX_UPLOAD_SIZE + 1), content_type='image/jpeg'
        )

        form = PlayerForm(
            data={'name': 'Test', 'surname': 'Player', 'email': 'a@example.com',
                  'birth_date': '01.01.1990', 'gender': 'M', 'country': 'UA'},
            files={'avatar': oversized_file},
            instance=player,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_player_form_rejects_disallowed_format_avatar(self):
        user = User.objects.create_user(username='avatar_format_test')
        player = Player.objects.create(
            user=user, name='Test', surname='Player', birth_date=date(1990, 1, 1),
        )
        bmp_file = _make_uploaded_image(10, 10, image_format='BMP', file_name='avatar.bmp',
                                         content_type='image/bmp')

        form = PlayerForm(
            data={'name': 'Test', 'surname': 'Player', 'email': 'a@example.com',
                  'birth_date': '01.01.1990', 'gender': 'M', 'country': 'UA'},
            files={'avatar': bmp_file},
            instance=player,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_player_form_accepts_valid_avatar(self):
        user = User.objects.create_user(username='avatar_valid_test')
        player = Player.objects.create(
            user=user, name='Test', surname='Player', birth_date=date(1990, 1, 1),
        )
        valid_file = _make_uploaded_image(100, 100, image_format='JPEG', file_name='avatar.jpg')

        form = PlayerForm(
            data={'name': 'Test', 'surname': 'Player', 'email': 'a@example.com',
                  'birth_date': '01.01.1990', 'gender': 'M', 'country': 'UA'},
            files={'avatar': valid_file},
            instance=player,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_club_admin_form_rejects_oversized_logo(self):
        # Django admin builds its ModelForm the same way modelform_factory does —
        # this proves the validators are shared between the profile and admin paths
        # without needing a full AdminSite/RequestFactory round trip.
        ClubForm = django_forms.modelform_factory(Club, fields=['name', 'short_name', 'address', 'logo'])
        oversized_file = SimpleUploadedFile(
            'big.jpg', b'x' * (settings.MAX_UPLOAD_SIZE + 1), content_type='image/jpeg'
        )

        form = ClubForm(
            data={'name': 'Test Club', 'short_name': 'TC', 'address': 'Test address'},
            files={'logo': oversized_file},
        )

        self.assertFalse(form.is_valid())
        self.assertIn('logo', form.errors)

    def test_player_form_accepts_blank_avatar(self):
        # avatar is optional (blank=True, null=True) — validators must not run on an
        # empty upload, and existing players/clubs without an avatar/logo must keep saving.
        user = User.objects.create_user(username='avatar_blank_test')
        player = Player.objects.create(
            user=user, name='Test', surname='Player', birth_date=date(1990, 1, 1),
        )

        form = PlayerForm(
            data={'name': 'Test', 'surname': 'Player', 'email': 'a@example.com',
                  'birth_date': '01.01.1990', 'gender': 'M', 'country': 'UA'},
            files={},
            instance=player,
        )

        self.assertTrue(form.is_valid(), form.errors)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.ImageFieldValidationTests -v 2
```
Expected: FAIL — `form.is_valid()` returns `True` for the oversized/BMP cases (no validators
attached yet), so `assertFalse` / `assertIn('avatar', form.errors)` assertions fail.

- [ ] **Step 3: Attach validators to the model fields**

In `components/web-api/application/federation/models/player.py`, add to the imports (top of
file, alongside the existing imports):

```python
from django.core.validators import FileExtensionValidator
from federation.validators import (
    validate_image_dimensions,
    validate_image_file_size,
    validate_image_format,
)
```

Change line 58 from:

```python
    avatar = models.ImageField(_('avatar'), blank=True, null=True, storage=MediaStorage())
```

to:

```python
    avatar = models.ImageField(
        _('avatar'), blank=True, null=True, storage=MediaStorage(),
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            validate_image_file_size,
            validate_image_dimensions,
            validate_image_format,
        ],
    )
```

In `components/web-api/application/federation/models/club.py`, add to the imports:

```python
from django.core.validators import FileExtensionValidator
from federation.validators import (
    validate_image_dimensions,
    validate_image_file_size,
    validate_image_format,
)
```

Change line 11 from:

```python
    logo  = models.ImageField(_('avatar'), blank=True, null=True, storage=MediaStorage())
```

to:

```python
    logo = models.ImageField(
        _('avatar'), blank=True, null=True, storage=MediaStorage(),
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            validate_image_file_size,
            validate_image_dimensions,
            validate_image_format,
        ],
    )
```

- [ ] **Step 4: Generate and inspect the migration**

Run:
```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py makemigrations federation
```
Expected: a new file `federation/migrations/00NN_alter_club_logo_alter_player_avatar.py` (exact
number/name depends on Django's auto-naming) containing only `AlterField` operations for
`club.logo` and `player.avatar` with the new `validators=` kwarg — no other field changes. Open
the generated file and confirm this before proceeding; do not hand-edit it.

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation.tests.ImageFieldValidationTests -v 2
```
Expected: `OK` with all 5 tests passing.

- [ ] **Step 6: Run the full test suite to check for regressions**

Run:
```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation
```
Expected: `OK`, no failures introduced elsewhere (e.g. fixture-based tests that create
`Player`/`Club` instances with no avatar/logo should be unaffected since both fields remain
`blank=True, null=True`).

- [ ] **Step 7: Commit**

```bash
git add components/web-api/application/federation/models/player.py components/web-api/application/federation/models/club.py components/web-api/application/federation/migrations/ components/web-api/application/federation/tests.py
git commit -m "feat(federation): enforce image validators on Player.avatar and Club.logo"
```

---

### Task 4: Remove dead validation code and surface errors in the profile template

**Files:**
- Modify: `components/web-api/application/federation/forms/player_form.py:82-93`
- Modify: `components/web-api/application/federation/templates/forms/profile/image_field.html`

**Interfaces:**
- Consumes: `Player.avatar` field validators (Task 3) — errors now populate
  `profile_form.errors['avatar']` when `PlayerForm.is_valid()` is called from
  `federation/views/profile.py` (no view changes needed — it already re-renders `profile_form`
  with errors intact when `is_valid()` returns `False`).

- [ ] **Step 1: Remove the dead `clean_content` method**

In `components/web-api/application/federation/forms/player_form.py`, delete lines 82-93:

```python
    def clean_content(self):
        content = self.cleaned_data['content']
        content_type = content.content_type.split('/')[0]
        if content_type in settings.CONTENT_TYPES:
            if content._size > settings.MAX_UPLOAD_SIZE:
                raise forms.ValidationError(_('Please keep filesize under %(max_size)s. Current filesize %(current_size)s') % {
                    'max_size': filesizeformat(settings.MAX_UPLOAD_SIZE),
                    'current_size': filesizeformat(content._size),
                })
        else:
            raise forms.ValidationError(_('File type is not supported'))
        return content

```

It referenced a `content` field that doesn't exist on `PlayerForm` and never ran — validation
now happens on the model field itself (Task 3).

Also remove the now-unused `from django.template.defaultfilters import filesizeformat` import
at the top of the file if nothing else in the file uses `filesizeformat` (check with
`grep -n filesizeformat components/web-api/application/federation/forms/player_form.py` after
the deletion — it should return nothing else).

- [ ] **Step 2: Render avatar field errors in the profile template**

`components/web-api/application/federation/templates/forms/profile/image_field.html` currently
renders the file input but never renders `field.errors`, so a rejected upload would silently
fail to show why. Current content:

```html
{% load static i18n %}
<div class="mb-3">
    <div class="d-flex flex-column align-items-center">
        {% if field.value %}
            <img src="{{ field.value.url }}?{{ field.value.instance.updated_at|date:'U' }}" class="img-thumbnail avatar mb-2" style="width: 150px; height: 150px; object-fit: cover;"/>
        {% else %}
            <img src="{% static 'default.png' %}" class="img-thumbnail avatar mb-2" style="width: 150px; height: 150px; object-fit: cover;"/>
        {% endif %}
    </div>

    <label class="form-label mt-2">{% trans "Choose a new photo" %}</label>
    <input class="form-control" type="file" name="{{ field.name }}" id="{{ field.id_for_label }}">
</div>
```

Replace with (adds error rendering below the input, using the `text-danger` class already used
for form errors elsewhere in this project — see `federation/templates/password_reset/confirm.html`):

```html
{% load static i18n %}
<div class="mb-3">
    <div class="d-flex flex-column align-items-center">
        {% if field.value %}
            <img src="{{ field.value.url }}?{{ field.value.instance.updated_at|date:'U' }}" class="img-thumbnail avatar mb-2" style="width: 150px; height: 150px; object-fit: cover;"/>
        {% else %}
            <img src="{% static 'default.png' %}" class="img-thumbnail avatar mb-2" style="width: 150px; height: 150px; object-fit: cover;"/>
        {% endif %}
    </div>

    <label class="form-label mt-2">{% trans "Choose a new photo" %}</label>
    <input class="form-control" type="file" name="{{ field.name }}" id="{{ field.id_for_label }}">
    {% if field.errors %}
        <div class="text-danger mt-1">{{ field.errors }}</div>
    {% endif %}
</div>
```

- [ ] **Step 3: Run the full test suite**

Run:
```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test federation
```
Expected: `OK`, no failures (in particular `PlayerProfileFormTests.test_profile_form_layout_renders_every_bound_field`
and the `ImageFieldValidationTests` class from Task 3 should still pass).

- [ ] **Step 4: Commit**

```bash
git add components/web-api/application/federation/forms/player_form.py components/web-api/application/federation/templates/forms/profile/image_field.html
git commit -m "fix(profile): remove dead avatar validation code and surface upload errors"
```

---

## Manual Verification (post-implementation, not automated)

After all tasks are complete, verify in a running local stack (`./deploy/local_run.sh`):

1. **Profile page** (`/profile/`): log in as a player, attempt to upload a >3 MB image → see the
   translated file-size error rendered under the avatar input. Attempt to upload a valid small
   JPEG/PNG/WebP → succeeds and avatar updates. Attempt to upload a GIF → rejected with format
   error.
2. **Django admin**: edit a `Player` and a `Club` record, attempt the same oversized/wrong-format
   uploads on `avatar`/`logo` → confirm the same validation errors appear via the default admin
   field-error UI.
3. Confirm existing players/clubs with no avatar/logo (blank) still save fine in both admin and
   profile forms — the fields remain optional.
