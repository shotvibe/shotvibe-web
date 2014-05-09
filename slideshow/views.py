from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.template import RequestContext
from django.views.decorators.cache import never_cache

from photos.models import Album

def index(request):
    return render_to_response('slideshow/index.html', {}, context_instance=RequestContext(request))


def slideshow(request, album_id):
    album = get_object_or_404(Album, pk=album_id)

    data = {
            'album': album
            }
    return render_to_response('slideshow/slideshow.html', data, context_instance=RequestContext(request))


@never_cache
def slideshow_latest_photo(request, album_id):
    album = get_object_or_404(Album, pk=album_id)

    latest_photo = album.photo_set.order_by('-album_index')[0]

    return redirect(latest_photo.get_photo_url_no_ext() + '_r_fhd.jpg')
