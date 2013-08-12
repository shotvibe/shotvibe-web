import random
import tempfile

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.contrib import auth

#from django.http import HttpResponseNotModified
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from photos_api.permissions import IsUserInAlbum, UserDetailsPagePermission, \
    IsSameUserOrStaff
from photos_api.parsers import PhotoUploadParser
from photos_api.signals import photos_added_to_album, member_leave_album

from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.reverse import reverse
from rest_framework.response import Response
#from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework import status
from rest_framework import views

import phonenumbers

from photos.image_uploads import handle_file_upload
from photos.models import Album, PendingPhoto, AlbumMember
from photos_api.serializers import AlbumNameSerializer, AlbumSerializer, UserSerializer, AlbumUpdateSerializer, AlbumAddSerializer
from photos_api.check_modified import supports_last_modified, supports_etag


@api_view(['GET'])
def api_root(request, format=None):
    """
    The entry endpoint of our API.
    """
    response_data = {
        'all_albums': reverse('album-list', request=request),
        'all_users': reverse('user-list', request=request),
        'upload_photos_request': reverse('photos-upload-request', request=request),
    }
    return Response(response_data)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def delete_account(request):
    """
    This function is very dangerous!

    It will delete the user account and all associated data, including:
    - All photos added
    - All albums created, including all of the contained photos, even if other users added them!
    """
    request.user.delete()

    return Response()

class AlbumList(generics.ListAPIView):
    """
    The list of all albums in the database, of all users.
    """
    permission_classes = (IsAdminUser,)
    model = Album
    serializer_class = AlbumNameSerializer


def parse_phone_number(phone_number, default_country):
    try:
        number = phonenumbers.parse(phone_number, default_country)
    except phonenumbers.phonenumberutil.NumberParseException:
        return None

    if not phonenumbers.is_possible_number(number):
        return None

    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)

@supports_etag
class AlbumDetail(generics.RetrieveAPIView):
    model = Album
    serializer_class = AlbumSerializer
    permission_classes = (IsUserInAlbum,)

    def initial(self, request, pk, *args, **kwargs):
        self.album = get_object_or_404(Album, pk=pk)
        return super(AlbumDetail, self).initial(request, pk, *args, **kwargs)

    def get_etag(self, request, pk):
        return self.album.get_etag()

    def post(self, request, pk):
        serializer = AlbumUpdateSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if serializer.object.add_photos:
            now = timezone.now()

            # Upload pending photos. For photos that already uploaded this will simply return photo
            pending_photos = PendingPhoto.objects.filter(photo_id__in=serializer.object.add_photos)
            photos = [pf.get_or_process_uploaded_image_and_create_photo(self.album, now) for pf in pending_photos]

            photos_added_to_album.send(sender=self,
                                       photos=photos,
                                       by_user=request.user,
                                       to_album=self.album)

        self.album.add_members(request.user, member_identifiers=serializer.object.add_members)

        responseSerializer = AlbumSerializer(self.album)
        return Response(responseSerializer.data)

class LeaveAlbum(generics.DestroyAPIView):
    model = AlbumMember
    permission_classes = (IsAuthenticated, IsUserInAlbum)

    def post(self, request, *args, **kwargs):
        album = self.get_object().album
        response = self.delete(request, *args, **kwargs)

        member_leave_album.send(sender=self, user=request.user, album=album)

        return response

    def get_object(self, queryset=None):

        if queryset is None:
            queryset = self.get_queryset()

        # pk from URL points to the album, not AlbumMember
        album_pk = self.kwargs.get(self.pk_url_kwarg, None)
        if album_pk is None:
            raise AttributeError("Missing Album pk")

        try:
            obj = queryset.get(user=self.request.user, album__pk=album_pk)
        except self.model.DoesNotExist:
            # This should never happen since we already checked if this records exists by checking permissions
            raise Http404(_(u"Album not found"))
        return obj


class UserList(generics.ListCreateAPIView):
    """
    API endpoint that represents a list of users.
    """
    model = auth.get_user_model()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveUpdateAPIView):
    """
    API endpoint that represents a single user.
    """
    model = auth.get_user_model()
    serializer_class = UserSerializer
    permission_classes = (UserDetailsPagePermission,)

    # These attributes can be changed with PUT or PATCH request
    __allowed_attributes_to_change = ['nickname']

    def __check_update_attr_permissions(self, request):
        """Ensure that only allowed attributes can be changed"""
        for key, value in request.DATA.iteritems():
            if key not in self.__allowed_attributes_to_change:
                raise PermissionDenied("You are not allowed to "
                                       "change '{0}'".format(key))

    def get_queryset(self):
        """For PUT and PATCH requests limit queryset to only user
        who makes request"""

        if self.request.method in ['PUT', 'PATCH']:
            return self.model.objects.filter(pk=self.request.user.pk)

        return super(UserDetail, self).get_queryset()

    def put(self, request, *args, **kwargs):
        """PUT handler"""
        self.__check_update_attr_permissions(request)
        return super(UserDetail, self).put(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """PATCH handler"""
        self.check_permissions(request)
        self.__check_update_attr_permissions(request)
        return super(UserDetail, self).patch(request, *args, **kwargs)


class UserAvatarDetail(views.APIView):
    """View that handles avatar uploads"""
    permission_classes = (IsAuthenticated, IsSameUserOrStaff)

    parser_classes = (PhotoUploadParser,)

    def process_upload_request(self, request, uploaded_chunks):
        """Uploads user avatar to the randomly picked location
        where we host user avatars and returns Response"""

        avatar_image_filename = settings.AVATAR_FILENAME_FORMAT_STRING.format(
            user_id=request.user.id,
            timestamp=timezone.now().strftime("%s")
        )
        avatar_location_format_str = random.choice(settings.AVATAR_BUCKETS)
        storage, bucket_name, filename = avatar_location_format_str.split(":")

        # Write uploaded data to temporary file
        # File will be delete once handler is closed
        temp_file = tempfile.TemporaryFile()
        for chunk in uploaded_chunks:
            temp_file.write(chunk)
        temp_file.seek(0)

        if storage == "s3":
            # Upload to S3
            try:
                conn = S3Connection(settings.AWS_ACCESS_KEY,
                                    settings.AWS_SECRET_ACCESS_KEY)
                bucket = conn.get_bucket(bucket_name)
                key = Key(bucket, avatar_image_filename)
                key.metadata = {'Content-Type': 'image/jpeg'}
                key.set_contents_from_file(temp_file)
                # Otherwise it's not accessible
                key.make_public()
                key.close(fast=True)
                temp_file.close()
            except:
                temp_file.close()
                raise
        else:
            temp_file.close()
            raise ValueError("Failed to upload avatar. "
                             "Unknown storage '{0}'.".format(storage))

        request.user.avatar_file = avatar_location_format_str.format(
            filename=avatar_image_filename)
        request.user.save()

        return Response()

    def post(self, request, *args, **kwargs):
        return self.process_upload_request(request,
                                           request.FILES['photo'].chunks())

    def put(self, request, *args, **kwargs):
        return self.process_upload_request(request,
                                           request.DATA.chunks())


@supports_last_modified
class Albums(generics.ListAPIView):
    """
    This Resource supports the "If-Modified-Since" HTTP header.

    Clients should remember the value returned in the "Date" HTTP header, and
    use this as the value of "If-Modified-Since" for future requests.

    If there have been no updates to the resource, the server will return an
    empty response body, and a status code of: 304 Not Modified
    """
    serializer_class = AlbumNameSerializer
    permission_classes = (IsAuthenticated,)

    def initial(self, request, *args, **kwargs):
        if request.user.is_staff:
            self.albums = Album.objects.all()
        elif request.user.is_authenticated():
            self.albums = Album.objects.get_user_albums(self.request.user.id)

        return super(Albums, self).initial(request, *args, **kwargs)

    def last_modified(self, request):
        last_modified = None
        for album in self.albums:
            if not last_modified or album.last_updated > last_modified:
                last_modified = album.last_updated
        return last_modified

    def get_queryset(self):
        return self.albums

    def post(self, request):
        serializer = AlbumAddSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        now = timezone.now()

        album = Album.objects.create_album(self.request.user, serializer.object.album_name)
        album.add_members(request.user, member_identifiers=serializer.object.members)

        for pending_photo in PendingPhoto.objects.filter(photo_id__in=serializer.object.photos):
            pending_photo.get_or_process_uploaded_image_and_create_photo(album, now)

        responseSerializer = AlbumSerializer(album)
        return Response(responseSerializer.data)

@api_view(['POST'])
@permission_classes((IsAuthenticated, ))
def photos_upload_request(request, format=None):
    """
    Use the GET parameter `num_photos` to specify how many photos you would
    like to upload
    """
    num_photos = int(request.GET.get('num_photos', 1))

    response_data = []
    for i in xrange(num_photos):
        pending_photo = PendingPhoto.objects.create(author=request.user)
        response_data.append({
            'photo_id': pending_photo.photo_id,
            'upload_url': reverse('photo-upload', [pending_photo.photo_id], request=request)
            })

    return Response(response_data)


class PhotoUpload(views.APIView):
    permission_classes = (IsAuthenticated,)

    parser_classes = (PhotoUploadParser,)

    def process_upload_request(self, request, photo_id, uploaded_chunks):
        pending_photo = get_object_or_404(PendingPhoto, pk=photo_id)
        if pending_photo.author != request.user:
            return Response(status=403)

        location, directory = pending_photo.bucket.split(':')
        if location != 'local':
            raise ValueError('Unknown photo bucket location: ' + location)

        handle_file_upload(directory, photo_id, uploaded_chunks)

        return Response()

    def post(self, request, photo_id, format=None):
        return self.process_upload_request(request, photo_id,
                                           request.FILES['photo'].chunks())

    def put(self, request, photo_id, format=None):
        return self.process_upload_request(request, photo_id,
                                           request.DATA.chunks())
