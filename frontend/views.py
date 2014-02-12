from django.conf import settings
from django.contrib import auth
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils import timezone
from django.db import transaction

import requests

from phone_auth.models import AuthToken
from photos.models import Album, Photo, AlbumMember
from photos import image_uploads
from photos import photo_operations
from photos_api.serializers import MemberIdentifier
from photos_api.signals import photos_added_to_album


def index(request):
    if request.user.is_authenticated():
        return home(request)
    else:
        return render_to_response('frontend/index.html', {}, context_instance=RequestContext(request))

def home(request):
    if request.method == 'POST' and 'create_album' in request.POST:
        album_name = request.POST.get('album_name', '').strip()
        if album_name:
            now = timezone.now()
            album = Album.objects.create_album(
                    creator = request.user,
                    name = album_name,
                    date_created = now)
            return HttpResponseRedirect(reverse('frontend.views.album', args=[album.id]))

    albums = Album.objects.get_user_albums(request.user.id).order_by('-last_updated')
    data = {
            'albums': albums
            }
    return render_to_response('frontend/home.html', data, context_instance=RequestContext(request))

@transaction.non_atomic_requests
def album(request, pk):
    album = get_object_or_404(Album, pk=pk)
    if not album.is_user_member(request.user.id):
        # TODO ...
        pass

    num_photos_added = 0
    num_photos_failed = 0

    if request.POST:
        if 'add_photos' in request.POST:
            pending_photo_ids = []
            for f in request.FILES.getlist('photo_files'):

                pending_photo = Photo.objects.upload_request(author=request.user)

                if settings.USING_LOCAL_PHOTOS:
                    image_uploads.process_file_upload(pending_photo, f.chunks())
                else:
                    # Forward request to photo upload server
                    userAuthToken = AuthToken.objects.create_auth_token(request.user, 'Internal Photo Upload Auth Token', timezone.now())

                    r = requests.put(settings.PHOTO_UPLOAD_SERVER_FORWARD_URL.format(pending_photo.photo_id),
                            headers = { 'Authorization': 'Token ' + userAuthToken.key },
                            data = f.chunks())
                    r.raise_for_status()

                pending_photo_ids.append(pending_photo.photo_id)
                num_photos_added += 1

            # Upload pending photos
            now = timezone.now()
            photo_operations.add_pending_photos_to_album(pending_photo_ids, album.id, now)

            # TODO: If this function will be refactored to use Class Based Views
            # change sender from `request` to `self` (View instance)
            photos_added_to_album.send(sender=request,
                                       photos=pending_photo_ids,
                                       by_user=request.user,
                                       to_album=album)

    data = {
            'album': album,
            'photos': album.get_photos(),
            'members': album.get_member_users(),
            'num_photos_added': num_photos_added,
            'num_photos_failed': num_photos_failed
            }
    return render_to_response('frontend/album.html', data, context_instance=RequestContext(request))

def photo(request, album_pk, photo_id):
    album = get_object_or_404(Album, pk=album_pk)
    photo = get_object_or_404(Photo, pk=photo_id)
    if photo.album != album:
        # TODO ...
        pass

    data = {
            'album': album,
            'photo': photo,
            'members': album.members.all()
            }
    return render_to_response('frontend/photo.html', data, context_instance=RequestContext(request))

def album_members(request, album_pk):
    album = get_object_or_404(Album, pk=album_pk)
    if not album.is_user_member(request.user.id):
        # TODO ...
        pass

    if request.method == 'POST' and 'add_member' in request.POST:
        try:
            user = auth.get_user_model().objects.get(pk=request.POST.get('member_id', ''))
        except auth.get_user_model().DoesNotExist:
            # TODO Better error handling.
            raise
        else:
            album.add_members(request.user, [MemberIdentifier(user_id=user.id)])

    members = album.members.all()

    # Gather all of the friends of the user: anyone who is a member of a shared
    # album
    others = set()
    for a in Album.objects.get_user_albums(request.user.id):
        others.update(a.members.all())

    # Remove anyone who is already in this album
    others.difference_update(members)

    # Remove myself
    others.discard(request.user)

    data = {
            'album': album,
            'members': members,
            'others': others
            }
    return render_to_response('frontend/album_members.html', data, context_instance=RequestContext(request))
