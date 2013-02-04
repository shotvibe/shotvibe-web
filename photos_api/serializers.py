from django.contrib.auth.models import User
from rest_framework import serializers

from photos.models import Album, Photo

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'url', 'username')

    id = serializers.IntegerField(source='id')

class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ('photo_id', 'photo_url', 'date_created', 'author')

    photo_url = serializers.CharField(source='get_photo_url')

class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = ('id', 'name', 'date_created', 'last_updated', 'members', 'photos')

    photos = PhotoSerializer(source='get_photos')

    def get_name_field(self, model_field):
        return None

class AlbumNameSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Album
        fields = ('id', 'url', 'name', 'last_updated', 'etag')

    id = serializers.IntegerField(source='id')

    etag = serializers.IntegerField(source='get_etag')

    id.read_only = True

    blah = serializers.IntegerField()

class PhotoListField(serializers.WritableField):
    def from_native(self, data):
        result = []
        for p in data:
            result.append(p['photo_id'])
        return result

class AlbumUpdate(object):
    def __init__(self, add_photos=None):
        self.add_photos = add_photos or []

class AlbumUpdateSerializer(serializers.Serializer):
    add_photos = PhotoListField()

    def restore_object(self, attrs, instance=None):
        return AlbumUpdate(add_photos=attrs['add_photos'])
