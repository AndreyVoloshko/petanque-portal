# Image Upload Validation — Design

## Problem

`Player.avatar` and `Club.logo` (both `ImageField`s, S3-backed via `MediaStorage`) have no
effective upload validation:

- [`PlayerForm.clean_content()`](../../../components/web-api/application/federation/forms/player_form.py)
  validates a field named `content`, which does not exist on the form — it is dead code and
  never runs. Avatar uploads currently pass through with **no size or type checks**.
- Django admin (`PlayerAdmin`, `ClubAdmin`) exposes both fields via the default auto-generated
  `ModelForm` with **no validation at all**.
- Orphaned settings `CONTENT_TYPES = ['image']` and `MAX_UPLOAD_SIZE = "2621440"` in
  `api/settings.py` were clearly intended to drive this validation but were never correctly
  wired up (and `MAX_UPLOAD_SIZE` is a string, not an int).

This allows arbitrarily large and arbitrarily-formatted files to be uploaded as avatars/logos
from both the public profile page and the admin panel, inflating S3 storage and page weight.

## Scope

In scope: `Player.avatar`, `Club.logo` — the only two `ImageField`s in the system, uploadable
from the player profile form and the Django admin.

Out of scope: `Tournament.terms` and `Document.file` (both `FileField`s for non-image documents
— PDFs etc.) are explicitly excluded from this change.

## Requirements (confirmed with stakeholder)

- Max file size: **3 MB**.
- Allowed formats: **JPEG, PNG, WebP** (no GIF, BMP, TIFF, etc.).
- Max pixel dimensions: **4000×4000 px** (guards against small-file-size-but-huge-dimension
  images and decompression-bomb-style pixel counts).
- Behavior on violation: **reject with a clear validation error** — no silent auto-resize or
  re-encoding.
- Must apply identically to both the profile upload form and the Django admin.

## Approach

Use Django's built-in `django.core.validators.FileExtensionValidator` plus a small,
purpose-built validators module — no new third-party dependency. Pillow (already a project
dependency, and already used internally by `ImageField`) provides format/dimension inspection.

Two package alternatives were evaluated and rejected:

- **django-imagekit** — actively maintained, but built for image *processing* (thumbnails,
  resize-on-save specs), not validation. Adopting it would mean swapping field types for
  auto-resize behavior the stakeholder explicitly ruled out.
- **django-resized** — same "built for resizing, not rejection" mismatch, and appears
  under-maintained (no real commits visible since ~2022 despite a 2024 release) — fails the
  maintenance bar.

Validators are attached directly to the **model fields**, not the form. Model-field validators
run in every `ModelForm` built on that model — including Django admin's auto-generated form —
so one shared, tested validators module covers both upload surfaces with no duplicated logic.

## Design

### 1. `federation/validators.py` (new module)

- `validate_image_file_size(file)` — rejects if `file.size > settings.MAX_UPLOAD_SIZE`.
- `validate_image_dimensions(file)` — opens the file with Pillow and rejects if width or
  height exceeds `settings.MAX_IMAGE_DIMENSION_PX`.
- `validate_image_format(file)` — opens the file with Pillow and rejects unless the
  *actual detected format* (`Image.format`, not the filename extension) is in
  `settings.ALLOWED_IMAGE_FORMATS`. This catches extension-spoofing (e.g. a `.jpg`-named file
  that is actually a BMP).
- All three raise `django.core.exceptions.ValidationError` with a translated (`gettext`)
  message, consistent with the project's Ukrainian-locale convention.
- Paired on the field with Django's built-in
  `FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])` for a fast,
  friendly rejection before the file is even opened.

### 2. Settings (`api/settings.py`)

Replace the orphaned/broken settings with corrected, documented constants:

```python
MAX_UPLOAD_SIZE = 3 * 1024 * 1024  # 3 MB, applies to avatar/logo image uploads
MAX_IMAGE_DIMENSION_PX = 4000       # max width/height in pixels for avatar/logo uploads
ALLOWED_IMAGE_FORMATS = ['JPEG', 'PNG', 'WEBP']  # Pillow-detected formats, not extensions
```

`CONTENT_TYPES` is removed (superseded by `ALLOWED_IMAGE_FORMATS`).

### 3. Model changes

- `federation/models/player.py`: `avatar = models.ImageField(..., validators=[...])`
- `federation/models/club.py`: `logo = models.ImageField(..., validators=[...])`

Both use the same validator list: `[FileExtensionValidator(...), validate_image_file_size,
validate_image_dimensions, validate_image_format]`.

Adding `validators=` does not change the DB schema but does change Django's field state, so
`makemigrations` will generate a trivial migration.

### 4. Form/admin cleanup

- Remove the dead `clean_content` method from
  `federation/forms/player_form.py` (references a non-existent `content` field).
- No admin code changes needed — `ClubAdmin` and `PlayerAdmin` use default auto-generated
  forms, which will now enforce the model-field validators automatically.

### 5. Error messages

Each validator raises a translated, parameterized message, e.g.:

- "File size must not exceed %(max_size)s. Current file size: %(current_size)s."
- "Image dimensions must not exceed %(max)s×%(max)s px."
- "Unsupported image format. Allowed formats: JPEG, PNG, WebP."

Rendered via crispy-forms' existing error display in the profile form, and Django admin's
standard field-error display.

## Testing

New `federation/tests/test_image_validators.py` (existing `federation/tests.py` is a
placeholder per project convention — new test module is added rather than extending the
placeholder). Covers:

- Valid JPEG/PNG/WebP under all limits → passes.
- File exceeding 3 MB → rejected.
- Image exceeding 4000×4000 px → rejected.
- Disallowed format (e.g. GIF) → rejected.
- Extension-spoofing case: a file named `.jpg` whose actual content is a different format
  (e.g. BMP) → rejected by `validate_image_format` even though `FileExtensionValidator` passes.
- Blank/empty avatar or logo (fields are optional) → still allowed.

Manual verification: upload attempts through both the profile page avatar field and the
Django admin Player/Club edit forms, confirming identical error messages on both surfaces.

## Non-goals / explicitly out of scope

- No auto-resize, re-encoding, or thumbnail generation.
- No changes to `MediaStorage`/S3 configuration or filename hashing.
- No changes to `Tournament.terms` or `Document.file`.
- No backfill/reprocessing of images already stored before this change — validation applies
  only to new uploads going forward.
