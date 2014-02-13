from django.conf.urls import patterns, url

from affiliates import views

urlpatterns = patterns('',
    url(r'^(?P<slug>[a-zA-Z0-9]+)$', views.event_link),
)
