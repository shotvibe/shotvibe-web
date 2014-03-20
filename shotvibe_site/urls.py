from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin

import frontend.urls
import affiliates.urls
import affiliates.event_urls

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'shotvibe_site.views.home', name='home'),
    # url(r'^shotvibe_site/', include('shotvibe_site.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^', include(frontend.urls)),

    url(r'^affiliates/', include(affiliates.urls)),
    url(r'^go/', include(affiliates.event_urls)),

    url(r'^admin/processed_photos/', 'photos.views.processed_photos'),
    url(r'^admin/upp_status/', 'photos_api.device_push.upp_status'),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    import photos_api.urls

    urlpatterns += (
            url(r'^api/', include(photos_api.urls)),
            )

# During development, serve the photos from the local photo storage directory
if settings.USING_LOCAL_PHOTOS:
    def parse_filename(photo_filename):
        # Filenames are in one of the formats:
        #
        # photoid (photoid="photoid", suffix="")
        # photoid.jpg (photoid="photoid", suffix=".jpg")
        # photoid_tail.jpg (photoid="photoid", suffix="_tail.jpg")

        underscore_index = photo_filename.find("_")
        period_index = photo_filename.find(".")

        if underscore_index < 0 and period_index < 0:
            photo_id = photo_filename
            suffix = ''
        else:
            if underscore_index < 0:
                suffix_start_index = period_index
            elif period_index < 0:
                suffix_start_index = underscore_index
            else:
                if underscore_index < period_index:
                    suffix_start_index = underscore_index
                else:
                    suffix_start_index = period_index

            photo_id = photo_filename[:suffix_start_index]
            suffix = photo_filename[suffix_start_index:]

        return (photo_id, suffix)


    def serve_photo(request, subdomain, photo_filename):
        from django.shortcuts import get_object_or_404
        from django.http import HttpResponseNotFound
        from django.views.static import serve

        from photos.models import Photo

        photo_id, suffix = parse_filename(photo_filename)

        photo = get_object_or_404(Photo, pk=photo_id)

        if photo.subdomain != subdomain:
            return HttpResponseNotFound()

        return serve(request, photo.storage_id + suffix, settings.LOCAL_PHOTOS_DIRECTORY)

    urlpatterns += (
            url(r'^photos/(?P<subdomain>[\w-]+)/(?P<photo_filename>[\w.-]+)$', serve_photo),
            )
