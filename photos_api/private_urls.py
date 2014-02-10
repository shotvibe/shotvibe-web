from django.conf.urls import patterns, url

from photos_api import private_views

urlpatterns = patterns('',
    url(r'^photo_upload/init/$', private_views.photo_upload_init, name='photo-upload-init'),
)
