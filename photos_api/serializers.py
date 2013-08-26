from django.contrib import auth
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
        model = auth.get_user_model()
        fields = ('id', 'url', 'nickname', 'avatar_url', 'invite_status')

    id = serializers.IntegerField(source='id')

    avatar_url = serializers.CharField(source='get_avatar_url')
    invite_status = serializers.CharField(source='get_invite_status')

class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ('photo_id', 'photo_url', 'date_created', 'author')

    photo_url = serializers.CharField(source='get_photo_url')
    author = UserSerializer(source='author')

class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = ('id', 'name', 'date_created', 'last_updated', 'members', 'photos')

    photos = PhotoSerializer(source='get_photos')
    members = UserSerializer(source='get_member_users')

    def get_name_field(self, model_field):
        return None

class AlbumNameSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Album
        fields = ('id', 'url', 'name', 'last_updated', 'etag', 'latest_photos')

    id = serializers.IntegerField(source='id')

    etag = serializers.IntegerField(source='get_etag')

    latest_photos = PhotoSerializer(source='get_latest_photos')

    id.read_only = True

class PhotoListField(serializers.WritableField):
    def from_native(self, data):
        result = []
        for p in data:
            result.append(p['photo_id'])
        return result

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

class AlbumUpdate(object):
    def __init__(self, add_photos=None, add_members=None):
        self.add_photos = add_photos or []
        self.add_members = add_members or []

class AlbumUpdateSerializer(serializers.Serializer):
    add_photos = PhotoListField(required=False)
    add_members = ListField(MemberIdentifierSerializer, required=False)

    def restore_object(self, attrs, instance=None):
        return AlbumUpdate(add_photos=attrs.get('add_photos'), add_members=attrs.get('add_members'))

class AlbumAdd(object):
    def __init__(self, album_name=None, members=None, photos=None):
        self.album_name = album_name
        self.members = members
        self.photos = photos

class AlbumAddSerializer(serializers.Serializer):
    album_name = serializers.CharField()
    members = ListField(MemberIdentifierSerializer, blank=True)
    photos = PhotoListField(blank=True)

    def restore_object(self, attrs, instance=None):
        return AlbumAdd(album_name=attrs['album_name'], members=attrs['members'], photos=attrs['photos'])


class QueryPhonesRequestItemSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=40)
    contact_nickname = serializers.CharField(max_length=128)


class QueryPhonesRequestSerializer(serializers.Serializer):
    default_country = serializers.CharField(max_length=2)
    phone_numbers = QueryPhonesRequestItemSerializer(many=True)

    def validate_default_country(self, attrs, source):
        attrs['default_country'] = attrs['default_country'].upper()
        return attrs
