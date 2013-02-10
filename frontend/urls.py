from django.conf.urls import patterns, url

from frontend import views

urlpatterns = patterns('',
    url(r'^$', views.index),
    url(r'^album/(?P<pk>\d+)/$', views.album),
    url(r'^album/(?P<album_pk>\d+)/photo/(?P<photo_id>[\w-]+)/$', views.photo),
)
