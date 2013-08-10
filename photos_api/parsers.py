from django.core.files import File
from rest_framework.parsers import BaseParser


class PhotoUploadParser(BaseParser):

    # Accept any Content-Type
    media_type = '*/*'

    def parse(self, stream, media_type=None, parser_context=None):
        return File(stream)
