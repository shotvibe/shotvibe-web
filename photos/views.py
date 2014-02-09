from django.contrib import admin
from django.shortcuts import render_to_response
from django.template import RequestContext

from photos.models import Photo
from photos import image_uploads

@admin.site.admin_view
def processed_photos(request):
    unprocessed_photos = []
    already_processed_photos = []
    now_processed_photos = []
    num_processed = 0
    for photo in Photo.objects.all():
        if image_uploads.photo_is_processed(photo.storage_id):
            already_processed_photos.append(photo)
        else:
            if 'process_photos' in request.POST and num_processed < int(request.POST['num_photos']):
                image_uploads.process_uploaded_image(photo.storage_id)
                now_processed_photos.append(photo)
                num_processed += 1
            else:
                unprocessed_photos.append(photo)

    data = {
            'unprocessed_photos': unprocessed_photos,
            'already_processed_photos': already_processed_photos,
            'now_processed_photos': now_processed_photos,
            }
    return render_to_response('photos/processed_photos.html', data, context_instance=RequestContext(request))
