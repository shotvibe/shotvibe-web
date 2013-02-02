from django.contrib.auth.models import User
#from django.http import HttpResponseNotModified
from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.response import Response
#from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated
from rest_framework import status

from photos.models import Album
from photos_api.serializers import AlbumNameSerializer, AlbumSerializer, UserSerializer, AlbumUpdateSerializer
from photos_api.check_modified import supports_last_modified, supports_etag

@api_view(['GET'])
def api_root(request, format=None):
    """
    The entry endpoint of our API.
    """
    response_data = {
        'all_albums': reverse('album-list', request=request),
        'all_users': reverse('user-list', request=request),
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
        self.album.add_photos(serializer.object.add_photos, request.user)
        return self.get(request, pk)

class UserList(generics.ListCreateAPIView):
    """
    API endpoint that represents a list of users.
    """
    model = User
    serializer_class = UserSerializer

class UserDetail(generics.RetrieveAPIView):
    """
    API endpoint that represents a single user.
    """
    model = User
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
