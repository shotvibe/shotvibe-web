from django.conf.urls import patterns, url

from frontend import views
from frontend import mobile_views
import phone_auth.views

urlpatterns = patterns('',
    url(r'^$', views.index, name="index"),
    url(r'^about/$', views.about, name="about"),
    url(r'^help/$', views.help, name="help"),
    url(r'^policy/$', views.policy, name="policy"),
    url(r'^contact/$', views.contact, name="contact"),
    url(r'^terms/$', views.terms, name="terms"),

    url(r'^album/(?P<pk>\d+)/$', views.album),
    url(r'^album/(?P<album_pk>\d+)/photo/(?P<photo_id>[\w-]+)/$', views.photo),
    url(r'^album/(?P<album_pk>\d+)/members/$', views.album_members),
    url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'frontend/login.html'}),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}),
    url(r'^i/(?P<invite_code>[\w_-]+)/$', mobile_views.invite_page, name="invite_page"),
    url(r'^app_init/$', phone_auth.views.app_init),
    url(r'^app/$', mobile_views.get_app, name="get_app"),
    url(r'^request_sms/$', phone_auth.views.RequestSMS.as_view(), name="request_sms"),
)
