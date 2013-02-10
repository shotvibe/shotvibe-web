from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from photos.models import Album, Photo

def index(request):
    if request.user.is_authenticated():
        return home(request)
    else:
        return render_to_response('frontend/index.html', {}, context_instance=RequestContext(request))

def home(request):
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

    data = {
            'album': album,
            'photos': album.get_photos().order_by('-date_created'),
            'members': album.members.all()
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
