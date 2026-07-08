from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _
from PIL import Image


def _is_committed_field_file(file):
    return getattr(file, '_committed', False)


def validate_image_file_size(file):
    if _is_committed_field_file(file):
        return

    file_size = file.size
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(
            _('File size must not exceed %(max_size)s. Current file size: %(current_size)s.'),
            params={
                'max_size': filesizeformat(settings.MAX_UPLOAD_SIZE),
                'current_size': filesizeformat(file_size),
            },
        )


def validate_image_dimensions(file):
    if _is_committed_field_file(file):
        return

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
    if _is_committed_field_file(file):
        return

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


IMAGE_UPLOAD_VALIDATORS = [
    FileExtensionValidator(allowed_extensions=settings.ALLOWED_IMAGE_EXTENSIONS),
    validate_image_file_size,
    validate_image_dimensions,
    validate_image_format,
]
