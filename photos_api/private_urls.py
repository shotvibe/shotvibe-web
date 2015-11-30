from django.conf.urls import patterns, url

from photos_api import private_views

urlpatterns = patterns('',
    url(r'^photo_upload/(?P<photo_id>[\w-]+)/init/$', private_views.photo_upload_init, name='photo-upload-init'),
    url(r'^photo_upload/(?P<photo_id>[\w-]+)/file_uploaded/$', private_views.photo_file_uploaded, name='photo-file-uploaded'),
    url(r'^photo_processing/(?P<storage_id>[\w-]+)/done/$', private_views.photo_processing_done, name='photo-processing-done'),
    url(r'^video_object/(?P<storage_id>[\w-]+)/', private_views.video_object, name='video-object'),
    url(r'^photo_servers/register/$', private_views.photo_server_register, name='photo-server-register')
)
