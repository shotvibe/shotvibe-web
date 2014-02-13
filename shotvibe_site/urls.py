from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
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

# During development, serve the photos from the photo buckets
standard_photo_bucket_suffix = '{0}/{1}.jpg'
if settings.LOCAL_PHOTO_BUCKET_URL_FORMAT_STR.endswith(standard_photo_bucket_suffix):
    urlpatterns += static(
            prefix = settings.LOCAL_PHOTO_BUCKET_URL_FORMAT_STR[:-len(standard_photo_bucket_suffix)],
            document_root = settings.LOCAL_PHOTO_BUCKETS_BASE_PATH)
