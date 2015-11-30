from rest_framework import serializers

from photos.models import Video


class VideoObjectSerializer(serializers.Serializer):
    author_id = serializers.IntegerField()
    album_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=(
        ('processing', 'processing'),
        ('ready', 'ready'),
        ('invalid', 'invalid'),
    ))
    duration = serializers.IntegerField(required=False)
