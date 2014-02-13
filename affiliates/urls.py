from django.conf.urls import patterns, url

from affiliates import views

urlpatterns = patterns('',
    url(r'^$', views.index),
    url(r'^(?P<organization_code>[^/]+)/$', views.organization),
    url(r'^(?P<organization_code>[^/]+)/event/new$', views.create_event),
    url(r'^(?P<organization_code>[^/]+)/event/(?P<event_id>\d+)$', views.event_edit),
    url(r'^(?P<organization_code>[^/]+)/links/(?P<event_id>\d+)$', views.event_links),
    url(r'^(?P<organization_code>[^/]+)/invites/(?P<event_id>\d+)$', views.event_invites),
    url(r'^(?P<organization_code>[^/]+)/reports/(?P<event_id>\d+)$', views.event_reports),
)
