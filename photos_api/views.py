from io import BytesIO
from django.contrib import auth
#from django.http import HttpResponseNotModified
from django.core.files.base import ContentFile
from django.http import QueryDict
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.datastructures import MultiValueDict

from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.reverse import reverse
from rest_framework.response import Response
#from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated
from rest_framework import status
from rest_framework.views import APIView

from photos.image_uploads import handle_file_upload
from photos.models import Album, Photo, PendingPhoto
from photos_api import SocketFile
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
        now = timezone.now()
        for photo_id in serializer.object.add_photos:
            # TODO Catch exception
            Photo.objects.upload_to_album(photo_id, self.album, now)
        add_member_ids = []
        for member in serializer.object.add_members:
            if member.user_id:
                add_member_ids.append(member.user_id)
        self.album.add_members(add_member_ids, now)

        return self.get(request, pk)

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
        album = Album.objects.create_album(self.request.user, serializer.object.album_name, now)
        for member in serializer.object.members:
            if member.user_id:
                album.members.add(member.user_id)
            else:
                # TODO Add members from phone number
                pass
        for photo_id in serializer.object.photos:
            Photo.objects.upload_to_album(photo_id, album, now)
        return Response(status=status.HTTP_302_FOUND, headers={ 'Location': reverse('album-detail', [album.id], request=request) })

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
        photo_id = Photo.objects.upload_request(request.user)
        response_data.append({
            'photo_id': photo_id,
            'upload_url': reverse('photo-upload', [photo_id], request=request)
            })

    return Response(response_data)


@api_view(['POST', 'PUT'])
@permission_classes((IsAuthenticated, ))
def photo_upload(request, photo_id, format=None):
    pending_photo = get_object_or_404(PendingPhoto, pk=photo_id)
    if pending_photo.author != request.user:
        return Response(status=403)

    location, directory = pending_photo.bucket.split(':')
    if location != 'local':
        raise ValueError('Unknown photo bucket location: ' + location)

    # TODO: Raise proper exception if there is no 'photo'

    file_chunks = request.FILES.get('photo', ContentFile('')).chunks()
    # if request.method == 'PUT':
    #     uploaded_file = SocketFile(request.environ['wsgi.input'], request.META.get('CONTENT_LENGTH', 0))
    #     file_chunks = uploaded_file.chunks()
    # else:
    #     file_chunks = request.FILES.get('photo', ContentFile('')).chunks()

    handle_file_upload(directory, photo_id, file_chunks)

    return Response()

# This method has taken from HttpRequest from django.http.request (Django v1.5) to support file uploads
# using HTTP PUT method. The only change is added 'PUT' in first `if` statement.
# V.Prudnikov 13 March, 2013.
def _load_post_and_files(self):
    """Populate self._post and self._files if the content-type is a form type"""
    if self.method not in ['POST','PUT']:
        self._post, self._files = QueryDict('', encoding=self._encoding), MultiValueDict()
        return
    if self._read_started and not hasattr(self, '_body'):
        self._mark_post_parse_error()
        return

    if self.META.get('CONTENT_TYPE', '').startswith('multipart/form-data'):
        if hasattr(self, '_body'):
            # Use already read data
            data = BytesIO(self._body)
        else:
            data = self
        try:
            self._post, self._files = self.parse_file_upload(self.META, data)
        except:
            # An error occured while parsing POST data. Since when
            # formatting the error the request handler might access
            # self.POST, set self._post and self._file to prevent
            # attempts to parse POST data again.
            # Mark that an error occured. This allows self.__repr__ to
            # be explicit about it instead of simply representing an
            # empty POST
            self._mark_post_parse_error()
            raise
    elif self.META.get('CONTENT_TYPE', '').startswith('application/x-www-form-urlencoded'):
        self._post, self._files = QueryDict(self.body, encoding=self._encoding), MultiValueDict()
    else:
        self._post, self._files = QueryDict('', encoding=self._encoding), MultiValueDict()


class PhotoUploadView(APIView):
    permission_classes = (IsAuthenticated, )

    def _process_file_upload(self, request, format=None, **kwargs):
        photo_id = kwargs.get('photo_id')

        pending_photo = get_object_or_404(PendingPhoto, pk=photo_id)
        if pending_photo.author != request.user:
            return Response(status=403)

        location, directory = pending_photo.bucket.split(':')
        if location != 'local':
            raise ValueError('Unknown photo bucket location: ' + location)

        # TODO: Raise proper exception if there is no request.FILES['photo'] parameter.

        file_chunks = request.FILES.get('photo', ContentFile('')).chunks()
        handle_file_upload(directory, photo_id, file_chunks)
        return Response()


    def put(self, request, format=None, **kwargs):
        # Patch Request.
        request._load_post_and_tiles = _load_post_and_files
        return self._process_file_upload(request, format, **kwargs)


    def post(self, request, format=None, **kwargs):
        return self._process_file_upload(request, format, **kwargs)
