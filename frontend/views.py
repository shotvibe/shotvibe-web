from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils import timezone

from photos.models import Album, Photo, PendingPhoto
from photos import image_uploads

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
            now = timezone.now()
            for f in request.FILES.getlist('photo_files'):
                photo_id = Photo.objects.upload_request(request.user)
                pending_photo = PendingPhoto.objects.get(photo_id=photo_id)
                location, directory = pending_photo.bucket.split(':')
                if location != 'local':
                    raise ValueError('Unknown photo bucket location: ' + location)

                image_uploads.handle_file_upload(directory, photo_id, f.chunks())
                Photo.objects.upload_to_album(photo_id, album, now)
                num_photos_added += 1

    data = {
            'album': album,
            'photos': album.get_photos().order_by('-date_created'),
            'members': album.members.all(),
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
