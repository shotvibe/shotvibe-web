from django.conf.urls import patterns, url

from frontend import views

urlpatterns = patterns('',
    url(r'^$', views.index),
    url(r'^album/(?P<pk>\d+)/$', views.album),
    url(r'^album/(?P<album_pk>\d+)/photo/(?P<photo_id>[\w-]+)/$', views.photo),
    url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'frontend/login.html'}),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}),
)
