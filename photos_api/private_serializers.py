from rest_framework import serializers

from photos.models import Video


class VideoObjectSerializer(serializers.Serializer):
    client_upload_id = serializers.CharField()
    author_id = serializers.IntegerField()
    album_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=(
        ('processing', 'processing'),
        ('ready', 'ready'),
        ('invalid', 'invalid'),
    ))
    duration = serializers.IntegerField(required=False)

class PhotoObjectSerializer(serializers.Serializer):
    client_upload_id = serializers.CharField()
    author_id = serializers.IntegerField()
    album_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=(
        ('processing', 'processing'),
        ('ready', 'ready'),
        ('invalid', 'invalid'),
    ))
    youtube_id = serializers.CharField()