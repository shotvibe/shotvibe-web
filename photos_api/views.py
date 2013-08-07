from django.utils.translation import ugettext_lazy as _
from django.contrib import auth
#from django.http import HttpResponseNotModified
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.files import File
from photos_api import device_push

from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.reverse import reverse
from rest_framework.response import Response
#from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated
from rest_framework import status
from rest_framework import views
from rest_framework.parsers import BaseParser

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

class IsUserInAlbum(BasePermission):
    def has_permission(self, request, view, obj=None):
        if request.user.is_staff:
            return True
        album_id = int(view.kwargs['pk'])
        album = get_object_or_404(Album, pk=album_id)
        return album.is_user_member(request.user.id)

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

            # Send push notifications to the album members about just added photos
            device_push.broadcast_photos_added(
                album_id=self.album.id,
                author_id=request.user.id,
                album_name=self.album.name,
                author_name=request.user.nickname,
                num_photos=len(photos),
                user_ids=[membership.user.id for membership in AlbumMember.objects.filter(album=self.album).only('user__id')])


        self.album.add_members(request.user, member_identifiers=serializer.object.add_members)

        responseSerializer = AlbumSerializer(self.album)
        return Response(responseSerializer.data)

class LeaveAlbum(generics.DestroyAPIView):
    model = AlbumMember
    permission_classes = (IsAuthenticated, IsUserInAlbum)

    def post(self, request, *args, **kwargs):
        response = self.delete(request, *args, **kwargs)

        # Send push notification to the user.
        device_push.broadcast_album_list_sync(request.user.id)

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

class UserDetail(generics.RetrieveAPIView):
    """
    API endpoint that represents a single user.
    """
    model = auth.get_user_model()
    serializer_class = UserSerializer

class IsSameUser(BasePermission):
    def has_permission(self, request, view, obj=None):
        if request.user.is_staff:
            return True
        user_id = int(view.kwargs['pk'])
        return request.user.id == user_id

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

class PhotoUploadParser(BaseParser):

    # Accept any Content-Type
    media_type = '*/*'

    def parse(self, stream, media_type=None, parser_context=None):
        return File(stream)

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
        return self.process_upload_request(request, photo_id, request.FILES['photo'].chunks())

    def put(self, request, photo_id, format=None):
        return self.process_upload_request(request, photo_id, request.DATA.chunks())
