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
