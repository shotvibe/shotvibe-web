from django.shortcuts import get_object_or_404
from photos.models import Album
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


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
        return album.is_user_member(request.user.id)


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


class UpdateAllowedAttributesPermission(BasePermission):
    """Ensure that only allowed attributes can be changed"""

    def has_permission(self, request, view):
        if request.method in ['PUT', 'PATCH']:
            for key, value in request.DATA.iteritems():
                if key not in view.allowed_attributes_to_change:
                    raise PermissionDenied("You are not allowed to "
                                           "change '{0}'".format(key))
        return True
