from django.conf.urls import patterns, url

from slideshow import views

urlpatterns = patterns('',
        url(r'^$', views.index),
        url(r'^(?P<album_id>\d+)/$', views.slideshow),
        url(r'^(?P<album_id>\d+)/latest_photo/$', views.slideshow_latest_photo),
)
