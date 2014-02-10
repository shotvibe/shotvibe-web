from django.conf.urls import patterns, url

from photos_api import private_views

urlpatterns = patterns('',
    url(r'^photo_upload/(?P<photo_id>[\w-]+)/init/$', private_views.photo_upload_init, name='photo-upload-init'),
    url(r'^photo_upload/(?P<photo_id>[\w-]+)/complete/$', private_views.photo_upload_complete, name='photo-upload-complete'),
)
