from django.contrib import auth
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils import timezone

from photos.models import Album, Photo, PendingPhoto, AlbumMember
from photos import image_uploads
from photos_api.serializers import MemberIdentifier
from photos_api import device_push


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

def album(request, pk):
    album = get_object_or_404(Album, pk=pk)
    if not album.is_user_member(request.user.id):
        # TODO ...
        pass

    num_photos_added = 0
    num_photos_failed = 0

    if request.POST:
        if 'add_photos' in request.POST:
            pending_photos = []
            for f in request.FILES.getlist('photo_files'):

                pending_photo = PendingPhoto.objects.create(author=request.user)
                location, directory = pending_photo.bucket.split(':')
                if location != 'local':
                    raise ValueError('Unknown photo bucket location: ' + location)

                image_uploads.handle_file_upload(directory, pending_photo.photo_id, f.chunks())
                pending_photos.append(pending_photo)
                num_photos_added += 1

            # Upload pending photos
            photos = [pf.get_or_process_uploaded_image_and_create_photo(album) for pf in pending_photos]

            # Send push notifications to the album members about just added photos
            device_push.broadcast_photos_added(
                album_id=album.id,
                author_id=request.user.id,
                album_name=album.name,
                author_name=request.user.nickname,
                num_photos=len(photos),
                user_ids=[membership.user.id for membership in AlbumMember.objects.filter(album=album).only('user__id')])

    data = {
            'album': album,
            'photos': album.get_photos().order_by('-date_created'),
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
