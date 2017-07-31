from django.core.files.storage import FileSystemStorage
import time, hashlib, os

class OverwriteStorage(FileSystemStorage):

    def get_available_name(self, name, max_length=500):
        # User hashed timestamp as a name
        filename, file_extension = os.path.splitext(name)

        name = hashlib.md5(str(time.time()).encode('utf-8')).hexdigest() + file_extension
        return name