from django.contrib.auth.models import User
from rest_framework import serializers

from photos.models import Album, Photo

class ListField(serializers.WritableField):
    """
    Utility class for a field that is a list of serializable elements
    """
    def __init__(self, element_serializer_type, *args, **kwargs):
        super(ListField, self).__init__(*args, **kwargs)
        self.element_serializer_type = element_serializer_type

    def from_native(self, data):
        result = []
        for e in data:
            serializer = self.element_serializer_type(data=e)
            if not serializer.is_valid():
                # TODO better error handling
                raise serializer.errors
            result.append(serializer.object)
        return result

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

class MemberIdentifier(object):
    def __init__(self, user_id=None, phone_number=None, default_country=None):
        self.user_id = user_id
        self.phone_number = phone_number
        self.default_country = default_country

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return repr(self.__dict__)

class MemberIdentifierSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    phone_number = serializers.CharField(required=False)
    default_country = serializers.CharField(required=False, min_length=2, max_length=2)

    def restore_object(self, attrs, instance=None):
        if 'user_id' in attrs:
            return MemberIdentifier(user_id=attrs['user_id'])
        else:
            return MemberIdentifier(phone_number=attrs['phone_number'], default_country=attrs['default_country'])

class AlbumAdd(object):
    def __init__(self, album_name=None, members=None, photos=None):
        self.album_name = album_name
        self.members = members
        self.photos = photos

class AlbumAddSerializer(serializers.Serializer):
    album_name = serializers.CharField()
    members = ListField(MemberIdentifierSerializer)
    photos = PhotoListField()

    def restore_object(self, attrs, instance=None):
        return AlbumAdd(album_name=attrs['album_name'], members=attrs['members'], photos=attrs['photos'])
