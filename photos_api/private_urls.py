from django.conf.urls import patterns, url

from photos_api import private_views

urlpatterns = patterns('',
    url(r'^photo_upload/(?P<photo_id>[\w-]+)/init/$', private_views.photo_upload_init, name='photo-upload-init'),
    url(r'^photo_upload/(?P<photo_id>[\w-]+)/file_uploaded/$', private_views.photo_file_uploaded, name='photo-file-uploaded'),
    url(r'^photo_upload/(?P<photo_id>[\w-]+)/processing_done/$', private_views.photo_processing_done, name='photo-processing-done'),
)
