from django.conf import settings
from django.contrib.staticfiles.storage import ManifestFilesMixin
from storages.backends.s3boto3 import S3Boto3Storage
import time, hashlib, os


class StaticStorage(ManifestFilesMixin, S3Boto3Storage):
    location = settings.STATICFILES_LOCATION


class MediaStorage(S3Boto3Storage):
    location = settings.MEDIAFILES_LOCATION

    def get_available_name(self, name, max_length=500):
        # User hashed timestamp as a name
        filename, file_extension = os.path.splitext(name)

        name = hashlib.md5(str(time.time()).encode('utf-8')).hexdigest() + file_extension
        return name

class AvatarsStorage(S3Boto3Storage):
    location = settings.MEDIAFILES_LOCATION

    def get_available_name(self, name, max_length=500):
        # User hashed timestamp as a name
        filename, file_extension = os.path.splitext(name)

        name = hashlib.md5(str(time.time()).encode('utf-8')).hexdigest() + file_extension
        return name
