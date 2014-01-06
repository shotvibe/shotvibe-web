from django.utils.translation import ugettext_lazy as _
from django.contrib import auth
import phonenumbers
from rest_framework import serializers

from photos.models import Album, AlbumMember, Photo


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
                # raise serializer.errors
                raise serializers.ValidationError(serializer.errors.values()[0])
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


class StaticField(serializers.Field):
    def __init__(self, field_value):
        self.value = field_value
        super(StaticField, self).__init__()

    def field_to_native(self, obj, field_name):
        return self.to_native(self.value)


class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = ('id', 'name', 'date_created', 'last_updated', 'members', 'photos', 'num_new_photos', 'last_access')

    photos = PhotoSerializer(source='get_photos')
    members = UserSerializer(source='get_member_users')

    # These fields are only relevant to AlbumMember, but we provide them here
    # to ensure consistency in the API responses
    num_new_photos = StaticField(0)
    last_access = StaticField(None)

    def get_name_field(self, model_field):
        return None


class AlbumMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlbumMember
        fields = ('id', 'name', 'date_created', 'last_updated', 'members', 'photos', 'num_new_photos', 'last_access')

    id = serializers.IntegerField(source='album.id')
    name = serializers.Field(source='album.name')
    date_created = serializers.Field(source='album.date_created')
    last_updated = serializers.Field(source='album.last_updated')
    photos = PhotoSerializer(source='album.get_photos')
    members = UserSerializer(source='album.get_member_users')
    num_new_photos = serializers.IntegerField(source='get_num_new_photos')

    id.read_only = True


class AlbumNameSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Album
        fields = ('id', 'url', 'name', 'last_updated', 'etag', 'latest_photos')

    id = serializers.IntegerField(source='id')

    etag = serializers.IntegerField(source='get_etag')

    latest_photos = PhotoSerializer(source='get_latest_photos')

    id.read_only = True


class AlbumMemberNameSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AlbumMember
        fields = ('id', 'url', 'name', 'last_updated', 'etag', 'latest_photos', 'num_new_photos', 'last_access')

    id = serializers.IntegerField(source='album.id')
    url = serializers.HyperlinkedRelatedField(view_name='album-detail', source='album')
    name = serializers.Field(source='album.name')
    last_updated = serializers.Field(source='album.last_updated')
    etag = serializers.IntegerField(source='album.get_etag')
    latest_photos = PhotoSerializer(source='album.get_latest_photos')
    num_new_photos = serializers.IntegerField(source='get_num_new_photos')

    id.read_only = True


class PhotoListField(serializers.WritableField):
    def from_native(self, data):
        result = []
        for p in data:
            result.append(p['photo_id'])
        return result


class DeletePhotosSerializer(serializers.Serializer):
    photos = PhotoListField(source='photo_id')


class MemberIdentifier(object):
    def __init__(self, user_id=None, phone_number=None, default_country=None, contact_nickname=None):
        self.user_id = user_id
        self.phone_number = phone_number
        self.default_country = default_country
        self.contact_nickname = contact_nickname

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return repr(self.__dict__)

class MemberIdentifierSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    phone_number = serializers.CharField(required=False, error_messages={
        'invalid_phone_number':_('Phone number is invalid'),
        'not_possible_phone_number':_('This phone number is not possible'),
    })
    default_country = serializers.CharField(required=False, min_length=2, max_length=2)
    contact_nickname = serializers.CharField(required=False, error_messages={
        'required_with_phone_number':_('\'contact_nickname\' attribute is required when adding a new member using phone number.')
    })

    def validate(self, attrs):
        # `contact_nickname` is required when `phone_number` provided but not `user_id`
        if 'user_id' not in attrs and not attrs.get('contact_nickname'):
            raise serializers.ValidationError(self.fields['contact_nickname'].error_messages['required_with_phone_number'])

        # Validate phone number
        if 'user_id' not in attrs:
            try:
                number = phonenumbers.parse(attrs.get('phone_number'),
                                            attrs.get('default_country'))
            except phonenumbers.phonenumberutil.NumberParseException:
                raise serializers.ValidationError(self.fields['phone_number'].error_messages['invalid_phone_number'])

            if not phonenumbers.is_possible_number(number):
                raise serializers.ValidationError(self.fields['phone_number'].error_messages['not_possible_phone_number'])

            # Format final number.
            attrs['phone_number'] = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)

        return attrs


    def restore_object(self, attrs, instance=None):
        if 'user_id' in attrs:
            return MemberIdentifier(user_id=attrs['user_id'])
        else:
            return MemberIdentifier(
                phone_number=attrs['phone_number'],
                default_country=attrs['default_country'],
                contact_nickname=attrs['contact_nickname']
            )


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
    members = ListField(MemberIdentifierSerializer, required=False)
    photos = PhotoListField(required=False)

    def restore_object(self, attrs, instance=None):
        return AlbumAdd(album_name=attrs['album_name'], members=attrs['members'], photos=attrs['photos'])


class AlbumViewSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()

    def restore_object(self, attrs, instance=None):
        return attrs['timestamp']


class QueryPhonesRequestItemSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=40)
    contact_nickname = serializers.CharField(max_length=128)


class QueryPhonesRequestSerializer(serializers.Serializer):
    default_country = serializers.CharField(max_length=2)
    phone_numbers = QueryPhonesRequestItemSerializer(many=True)

    def validate_default_country(self, attrs, source):
        attrs['default_country'] = attrs['default_country'].upper()
        return attrs
