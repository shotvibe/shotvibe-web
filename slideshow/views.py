import datetime

from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.template import RequestContext
from django.views.decorators.cache import never_cache
from django.utils import timezone

from photos.models import Album

def index(request):
    return render_to_response('slideshow/index.html', {}, context_instance=RequestContext(request))


def slideshow(request, album_id):
    album = get_object_or_404(Album, pk=album_id)

    # Temporary hard-coded captions
    if album.id == 2794:
        caption = 'Maria & Niv'
    elif album.id == 2795:
        caption = 'Moran & Yaniv'
    elif album.id == 2963:
        caption = 'Limor & Itay\'s Wedding'
    else:
        caption = ''

    data = {
            'album': album,
            'caption': caption
            }
    return render_to_response('slideshow/slideshow.html', data, context_instance=RequestContext(request))


@never_cache
def slideshow_latest_photo(request, album_id):
    album = get_object_or_404(Album, pk=album_id)

    epoch_date = datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)
    epoch_seconds = int((timezone.now() - epoch_date).total_seconds())

    transition_time = 15
    cycles_length = 3

    current_cycle = (epoch_seconds % (transition_time * cycles_length)) / transition_time

    latest_photo = album.photo_set.order_by('-album_index')[current_cycle]

    return redirect(latest_photo.get_photo_url_no_ext() + '_r_fhd.jpg')
