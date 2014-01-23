from django.conf.urls import patterns, url

from frontend import views
from frontend import mobile_views
import phone_auth.views

urlpatterns = patterns('',
    url(r'^$', views.index),
    url(r'^album/(?P<pk>\d+)/$', views.album),
    url(r'^album/(?P<album_pk>\d+)/photo/(?P<photo_id>[\w-]+)/$', views.photo),
    url(r'^album/(?P<album_pk>\d+)/members/$', views.album_members),
    url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'frontend/login.html'}),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}),
    url(r'^i/(?P<invite_code>[\w_-]+)/$', mobile_views.invite_page, name="invite_page"),
    url(r'^app_init/$', phone_auth.views.app_init),
    # Temporary event for Dolev 2014-01-24
    url(r'^e/dolev/$', mobile_views.dolev_event, name="dolev_event"),
)
