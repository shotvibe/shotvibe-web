from django.conf import settings
from django.shortcuts import get_object_or_404
from photos.models import Album
from rest_framework.permissions import BasePermission

from rest_framework.authentication import get_authorization_header


class IsSameUserOrStaff(BasePermission):
    """Authorized user has the same pk as `pk` view keyword argument
    or is staff"""
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        user_id = int(view.kwargs['pk'])
        return request.user.id == user_id


class IsUserInAlbum(BasePermission):
    """Authenticated user is member of the album specified by pk view
     keyword argument or is staff"""
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        album_id = int(view.kwargs['pk'])
        album = get_object_or_404(Album, pk=album_id)
        return album.public or album.is_user_member(request.user.id)


class UserDetailsPagePermission(BasePermission):
    """This is used in UserDetailsView to ensure that user can update field
    only on himself

    This allows GET to anyone
    PUT and PATCH only to user himself
    Otherwise not allowed (including POST)
    """

    def has_permission(self, request, view):
        # POST (Create) is not allowed
        if request.method == 'POST':
            return False
        return super(UserDetailsPagePermission, self).has_permission(request,
                                                                     view)


    def has_object_permission(self, request, view, obj):

        # GET allowed for anyone
        if request.method == 'GET':
            return True

        # PUT and PATCH is allowed only for user himself
        if request.method in ['PUT', 'PATCH']:
            return request.user.is_authenticated and request.user == obj

        return super(UserDetailsPagePermission, self).\
            has_object_permission(request, view, obj)


class IsAllowedPrivateAPI(BasePermission):
    """
    Permission that requires that the client authenticate with a key allowing
    access to the private API. This is used by external servers.

    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string "Key ". For example:

    Authorization: Key 401f7ac837da42b97f613d789819ff93537bee6a
    """
    def has_permission(self, request, view):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'key':
            return None

        if len(auth) == 1:
            return False
        elif len(auth) > 2:
            return False

        return auth[1] == settings.PRIVATE_API_KEY
