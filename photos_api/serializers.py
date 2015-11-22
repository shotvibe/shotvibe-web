from django.utils.translation import ugettext_lazy as _
from django.contrib import auth
from rest_framework import serializers

from photos.models import Album, AlbumMember, Photo, PhotoComment, PhotoUserTag, PhotoGlanceScoreDelta, PhotoGlance


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


class UserGlanceScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = auth.get_user_model()
        fields = ('user_glance_score',)


class UserCompactSerializer(serializers.ModelSerializer):
    class Meta:
        model = auth.get_user_model()
        fields = ('id', 'nickname', 'avatar_url')

    id = serializers.IntegerField(source='id')
    avatar_url = serializers.CharField(source='get_avatar_url')


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoComment
        fields = ('date_created', 'author', 'client_msg_id', 'comment')

    comment = serializers.CharField(source='comment_text')
    author = UserCompactSerializer(source='author')


class UserTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoUserTag
        fields = ('tagged_user', 'tag_coord_x', 'tag_coord_y')

    tagged_user = UserCompactSerializer(source='tagged_user')


class GlanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoGlance
        fields = ('date_created', 'author', 'emoticon_name')

    author = UserCompactSerializer(source='author')


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ('photo_id', 'photo_url', 'date_created', 'author', 'comments', 'user_tags', 'global_glance_score', 'my_glance_score_delta', 'glances')

    def __init__(self, request_user=None, *args, **kwargs):
        self.request_user = request_user
        super(PhotoSerializer, self).__init__(*args, **kwargs)

    photo_url = serializers.CharField(source='get_photo_url')
    author = UserSerializer(source='author')
    global_glance_score = serializers.IntegerField(source='get_global_glance_score')
    my_glance_score_delta = serializers.SerializerMethodField('get_global_glance_score')
    comments = CommentSerializer(source='get_comments')
    user_tags = UserTagSerializer(source='get_user_tags')
    glances = GlanceSerializer(source='get_glances')

    def get_global_glance_score(self, photo):
        if not self.request_user:
            return 0

        return PhotoGlanceScoreDelta.objects.get_photo_user_glance_score_delta(self.request_user, photo)


class StaticField(serializers.Field):
    def __init__(self, field_value):
        self.value = field_value
        super(StaticField, self).__init__()

    def field_to_native(self, obj, field_name):
        return self.to_native(self.value)


def album_name_or_members(album_member):
    if album_member.album.name:
        return album_member.album.name
    else:
        other_users = album_member.get_other_members()
        other_users.sort(key=lambda u: u.id)
        return ", ".join([u.nickname for u in other_users])


class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = ('id', 'name', 'creator', 'date_created', 'last_updated', 'members', 'photos', 'num_new_photos', 'last_access')

    creator = UserSerializer(source='creator')
    photos = PhotoSerializer(source='get_photos')
    members = UserSerializer(source='get_member_users')

    # These fields are only relevant to AlbumMember, but we provide them here
    # to ensure consistency in the API responses
    num_new_photos = StaticField(0)
    last_access = StaticField(None)

    def get_name_field(self, model_field):
        return None


class AlbumNameChangeSerializer(serializers.Serializer):
    name = serializers.CharField()

class AlbumMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlbumMember
        fields = ('id', 'name', 'creator', 'date_created', 'last_updated', 'members', 'photos', 'num_new_photos', 'last_access')

    def __init__(self, *args, **kwargs):
        super(AlbumMemberSerializer, self).__init__(*args, **kwargs)
        request_user = kwargs['context']['request'].user
        self.fields['photos'] = PhotoSerializer(request_user, source='album.get_photos')

    id = serializers.IntegerField(source='album.id')
    name = serializers.SerializerMethodField('get_album_name')
    creator = UserSerializer(source='album.creator')
    date_created = serializers.Field(source='album.date_created')
    last_updated = serializers.Field(source='album.last_updated')
    photos = PhotoSerializer(source='album.get_photos')
    members = UserSerializer(source='album.get_member_users')
    num_new_photos = serializers.IntegerField(source='get_num_new_photos')

    id.read_only = True

    def get_album_name(self, album_member):
        return album_name_or_members(album_member)


class AlbumMemberPhoneNumberSerializer(serializers.Serializer):
    user = UserSerializer()
    phone_number = serializers.CharField()


class AlbumNameSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Album
        fields = ('id', 'url', 'name', 'creator', 'date_created', 'last_updated', 'etag', 'latest_photos')

    id = serializers.IntegerField(source='id')

    creator = UserSerializer(source='creator')

    etag = serializers.IntegerField(source='get_etag')

    latest_photos = PhotoSerializer(source='get_latest_photos')

    id.read_only = True


class AlbumMemberNameSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AlbumMember
        fields = ('id', 'url', 'name', 'creator', 'date_created', 'last_updated', 'etag', 'latest_photos', 'num_new_photos', 'latest_comment', 'last_access')

    id = serializers.IntegerField(source='album.id')
    url = serializers.HyperlinkedRelatedField(view_name='album-detail', source='album')
    name = serializers.SerializerMethodField('get_album_name')
    creator = UserSerializer(source='album.creator')
    date_created = serializers.Field(source='album.date_created')
    last_updated = serializers.Field(source='album.last_updated')
    etag = serializers.IntegerField(source='album.get_etag')
    latest_photos = PhotoSerializer(source='album.get_latest_photos')
    latest_comment = CommentSerializer(source='album.get_latest_comment')
    num_new_photos = serializers.IntegerField(source='get_num_new_photos')

    id.read_only = True

    def get_album_name(self, album_member):
        return album_name_or_members(album_member)

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
    phone_number = serializers.CharField(required=False)
    default_country = serializers.CharField(required=False, min_length=2, max_length=2)
    contact_nickname = serializers.CharField(required=False, error_messages={
        'required_with_phone_number':_('\'contact_nickname\' attribute is required when adding a new member using phone number.')
    })

    def validate(self, attrs):
        # `contact_nickname` is required when `phone_number` provided but not `user_id`
        if 'user_id' not in attrs and not attrs.get('contact_nickname'):
            raise serializers.ValidationError(self.fields['contact_nickname'].error_messages['required_with_phone_number'])

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


class AlbumMembersSerializer(serializers.Serializer):
    members = ListField(MemberIdentifierSerializer, required=False)


class AlbumUpdate(object):
    def __init__(self, add_photos=None, copy_photos=None, add_members=None):
        self.add_photos = add_photos or []
        self.copy_photos = copy_photos or []
        self.add_members = add_members or []


class AlbumUpdateSerializer(serializers.Serializer):
    add_photos = PhotoListField(required=False)
    copy_photos = PhotoListField(required=False)
    add_members = ListField(MemberIdentifierSerializer, required=False)

    def restore_object(self, attrs, instance=None):
        return AlbumUpdate(
                add_photos=attrs.get('add_photos'),
                copy_photos=attrs.get('copy_photos'),
                add_members=attrs.get('add_members'),
                )


class AlbumAdd(object):
    def __init__(self, album_name=None, members=None):
        self.album_name = album_name
        self.members = members


class AlbumAddSerializer(serializers.Serializer):
    album_name = serializers.CharField(required=False)
    members = ListField(MemberIdentifierSerializer, required=False)

    def restore_object(self, attrs, instance=None):
        return AlbumAdd(album_name=attrs['album_name'], members=attrs['members'])


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

class PhotoUploadInitSerializer(serializers.Serializer):
    user_auth_token = serializers.CharField()


class PhotoCommentSerializer(serializers.Serializer):
    comment = serializers.CharField()


class PhotoUserTagSerializer(serializers.Serializer):
    tag_coord_x = serializers.FloatField()
    tag_coord_y = serializers.FloatField()


class PhotoGlanceScoreSerializer(serializers.Serializer):
    score_delta = serializers.IntegerField()


class PhotoGlanceSerializer(serializers.Serializer):
    emoticon_name = serializers.CharField(max_length=255)


class PhotoServerRegisterSerializer(serializers.Serializer):
    update_url = serializers.CharField()
    subdomain = serializers.CharField()
    auth_key = serializers.CharField()
